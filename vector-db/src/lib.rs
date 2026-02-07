#![deny(clippy::all)]
#![allow(unsafe_op_in_unsafe_fn)]

use pyo3::prelude::*;
use pyo3::types::PyType;
use std::sync::{Arc, RwLock};
use usearch::Index;
use rusqlite::Connection;

/// 搜索结果 (返回 ID 而非 Tag 文本)
/// 上层 Python 会拿着 ID 去 SQLite 里查具体的文本内容
#[pyclass]
pub struct SearchResult {
    #[pyo3(get, set)]
    pub id: u32,
    #[pyo3(get, set)]
    pub score: f64,
}

#[pyclass]
pub struct SvdResult {
    #[pyo3(get, set)]
    pub u: Vec<f64>,
    #[pyo3(get, set)]
    pub s: Vec<f64>,
    #[pyo3(get, set)]
    pub k: u32,
    #[pyo3(get, set)]
    pub dim: u32,
}

#[pyclass]
pub struct OrthogonalProjectionResult {
    #[pyo3(get, set)]
    pub projection: Vec<f64>,
    #[pyo3(get, set)]
    pub residual: Vec<f64>,
    #[pyo3(get, set)]
    pub basis_coefficients: Vec<f64>,
}

#[pyclass]
pub struct HandshakeResult {
    #[pyo3(get, set)]
    pub magnitudes: Vec<f64>,
    #[pyo3(get, set)]
    pub directions: Vec<f64>,
}

#[pyclass]
pub struct ProjectResult {
    #[pyo3(get, set)]
    pub projections: Vec<f64>,
    #[pyo3(get, set)]
    pub probabilities: Vec<f64>,
    #[pyo3(get, set)]
    pub entropy: f64,
    #[pyo3(get, set)]
    pub total_energy: f64,
}

/// 统计信息
#[pyclass]
pub struct VexusStats {
    #[pyo3(get, set)]
    pub total_vectors: u32,
    #[pyo3(get, set)]
    pub dimensions: u32,
    #[pyo3(get, set)]
    pub capacity: u32,
    #[pyo3(get, set)]
    pub memory_usage: u32,
}

/// 核心索引结构 (无状态，只存向量)
#[pyclass]
pub struct VexusIndex {
    index: Arc<RwLock<Index>>,
    dimensions: u32,
}

#[pymethods]
impl VexusIndex {
    /// 创建新的空索引
    #[new]
    pub fn new(dim: u32, capacity: u32) -> PyResult<Self> {
        let index = Index::new(&usearch::IndexOptions {
            dimensions: dim as usize,
            metric: usearch::MetricKind::L2sq,
            quantization: usearch::ScalarKind::F32,
            connectivity: 16,
            expansion_add: 128,
            expansion_search: 64,
            multi: false,
        })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create index: {:?}", e)))?;

        index
            .reserve(capacity as usize)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to reserve capacity: {:?}", e)))?;

        Ok(Self {
            index: Arc::new(RwLock::new(index)),
            dimensions: dim,
        })
    }

    /// 从磁盘加载索引
    #[classmethod]
    #[pyo3(signature = (dim, capacity, index_path, _unused_map_path=None))]
    pub fn load(_cls: &Bound<'_, PyType>, dim: u32, capacity: u32, index_path: String, _unused_map_path: Option<String>) -> PyResult<Self> {
        let index = Index::new(&usearch::IndexOptions {
            dimensions: dim as usize,
            metric: usearch::MetricKind::L2sq,
            quantization: usearch::ScalarKind::F32,
            connectivity: 16,
            expansion_add: 128,
            expansion_search: 64,
            multi: false,
        })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create index wrapper: {:?}", e)))?;

        index.load(&index_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to load index from disk: {:?}", e)))?;

        let current_capacity = index.capacity();
        if capacity as usize > current_capacity {
            index
                .reserve(capacity as usize)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to expand capacity: {:?}", e)))?;
        }

        Ok(Self {
            index: Arc::new(RwLock::new(index)),
            dimensions: dim,
        })
    }

    /// 保存索引到磁盘
    pub fn save(&self, index_path: String) -> PyResult<()> {
        let index = self.index.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock failed: {}", e)))?;

        let temp_path = format!("{}.tmp", index_path);

        index
            .save(&temp_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to save index: {:?}", e)))?;

        std::fs::rename(&temp_path, &index_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to rename index file: {}", e)))?;

        Ok(())
    }

    /// 单个添加
    pub fn add(&self, id: u32, vector: Vec<u8>) -> PyResult<()> {
        let index = self.index.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock failed: {}", e)))?;

        let vec_slice: &[f32] = unsafe {
            std::slice::from_raw_parts(
                vector.as_ptr() as *const f32,
                vector.len() / std::mem::size_of::<f32>(),
            )
        };

        if vec_slice.len() != self.dimensions as usize {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Dimension mismatch: expected {}, got {}",
                self.dimensions,
                vec_slice.len()
            )));
        }

        if index.size() + 1 >= index.capacity() {
             let new_cap = (index.capacity() as f64 * 1.5) as usize;
             let _ = index.reserve(new_cap);
        }

        index
            .add(id as u64, vec_slice)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Add failed: {:?}", e)))?;

        Ok(())
    }

    /// 批量添加
    pub fn add_batch(&self, ids: Vec<u32>, vectors: Vec<u8>) -> PyResult<()> {
        let index = self.index.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock failed: {}", e)))?;

        let count = ids.len();
        let dim = self.dimensions as usize;

        let vec_slice: &[f32] = unsafe {
            std::slice::from_raw_parts(
                vectors.as_ptr() as *const f32,
                vectors.len() / std::mem::size_of::<f32>(),
            )
        };

        if vec_slice.len() != count * dim {
             return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Batch size mismatch".to_string()));
        }

        if index.size() + count >= index.capacity() {
            let new_cap = ((index.size() + count) as f64 * 1.5) as usize;
            let _ = index.reserve(new_cap);
        }

        for (i, id) in ids.iter().enumerate() {
            let start = i * dim;
            let v = &vec_slice[start..start+dim];
            index.add(*id as u64, v)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Batch add failed idx {}: {:?}", i, e)))?;
        }

        Ok(())
    }

    /// 搜索
    pub fn search(&self, query: Vec<u8>, k: u32) -> PyResult<Vec<SearchResult>> {
        let index = self.index.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock failed: {}", e)))?;

        let query_slice: &[f32] = unsafe {
            std::slice::from_raw_parts(
                query.as_ptr() as *const f32,
                query.len() / std::mem::size_of::<f32>(),
            )
        };

        if query_slice.len() != self.dimensions as usize {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Search dimension mismatch: expected {}, got {}. (Check your bytes input!)",
                self.dimensions,
                query_slice.len()
            )));
        }

        let matches = index
            .search(query_slice, k as usize)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Search failed: {:?}", e)))?;

        let mut results = Vec::with_capacity(matches.keys.len());

        for (key, &dist) in matches.keys.iter().zip(matches.distances.iter()) {
            results.push(SearchResult {
                id: *key as u32,
                score: 1.0 - dist as f64,
            });
        }

        Ok(results)
    }

    /// 删除 (按 ID)
    pub fn remove(&self, id: u32) -> PyResult<()> {
        let index = self.index.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock failed: {}", e)))?;

        index.remove(id as u64)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Remove failed: {:?}", e)))?;

        Ok(())
    }

    /// 获取当前索引状态
    pub fn stats(&self) -> PyResult<VexusStats> {
        let index = self.index.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock failed: {}", e)))?;

        Ok(VexusStats {
            total_vectors: index.size() as u32,
            dimensions: self.dimensions,
            capacity: index.capacity() as u32,
            memory_usage: index.memory_usage() as u32,
        })
    }

    /// 从 SQLite 数据库恢复索引 (同步版本)
    #[pyo3(signature = (db_path, table_type, filter_diary_name=None))]
    pub fn recover_from_sqlite(&self, db_path: String, table_type: String, filter_diary_name: Option<String>) -> PyResult<u32> {
        let conn = Connection::open(&db_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB: {}", e)))?;

        let sql: String;

        if table_type == "tags" {
            sql = "SELECT id, vector FROM tags WHERE vector IS NOT NULL".to_string();
        } else if table_type == "chunks" && filter_diary_name.is_some() {
            sql = "SELECT c.id, c.vector FROM chunks c JOIN files f ON c.file_id = f.id WHERE f.diary_name = ?1 AND c.vector IS NOT NULL".to_string();
        } else {
            return Ok(0);
        }

        let mut stmt = conn
            .prepare(&sql)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to prepare statement: {}", e)))?;

        let mut count = 0;
        let mut skipped_dim_mismatch = 0;
        let expected_byte_len = self.dimensions as usize * std::mem::size_of::<f32>();

        let index = self.index.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock failed: {}", e)))?;

        let mut process_row = |id: i64, vector_bytes: Vec<u8>| {
             if vector_bytes.len() == expected_byte_len {
                let vec_slice: &[f32] = unsafe {
                    std::slice::from_raw_parts(
                        vector_bytes.as_ptr() as *const f32,
                        self.dimensions as usize,
                    )
                };

                if index.size() + 1 >= index.capacity() {
                    let new_cap = (index.capacity() as f64 * 1.5) as usize;
                    let _ = index.reserve(new_cap);
                }

                if index.add(id as u64, vec_slice).is_ok() {
                    count += 1;
                }
            } else {
                skipped_dim_mismatch += 1;
            }
        };

        if let Some(name) = &filter_diary_name {
            let rows = stmt.query_map([name], |row| Ok((row.get::<_, i64>(0)?, row.get::<_, Vec<u8>>(1)?)))
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query failed: {}", e)))?;

            for row_result in rows {
                if let Ok((id, vector_bytes)) = row_result {
                    process_row(id, vector_bytes);
                }
            }
        } else {
            let rows = stmt.query_map([], |row| Ok((row.get::<_, i64>(0)?, row.get::<_, Vec<u8>>(1)?)))
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query failed: {}", e)))?;

            for row_result in rows {
                if let Ok((id, vector_bytes)) = row_result {
                    process_row(id, vector_bytes);
                }
            }
        }

        if skipped_dim_mismatch > 0 {
            println!("[Vexus-Lite] ⚠️ Skipped {} vectors due to dimension mismatch (Expected {} bytes, got various)", skipped_dim_mismatch, expected_byte_len);
        }

        Ok(count)
    }

    /// 高性能 SVD 分解
    pub fn compute_svd(&self, flattened_vectors: Vec<u8>, n: u32, max_k: u32) -> PyResult<SvdResult> {
        let dim = self.dimensions as usize;
        let n = n as usize;
        let max_k = max_k as usize;

        let vec_slice: &[f32] = unsafe {
            std::slice::from_raw_parts(
                flattened_vectors.as_ptr() as *const f32,
                flattened_vectors.len() / std::mem::size_of::<f32>(),
            )
        };

        if vec_slice.len() != n * dim {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Flattened vectors length mismatch: expected {}, got {}",
                n * dim,
                vec_slice.len()
            )));
        }

        use nalgebra::DMatrix;
        let matrix = DMatrix::from_row_slice(n, dim, vec_slice);
        let svd = matrix.svd(false, true);

        let s = svd.singular_values.as_slice().iter().map(|&x| x as f64).collect::<Vec<_>>();
        let v_t = svd.v_t.ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to compute V^T matrix".to_string()))?;

        let k = std::cmp::min(s.len(), max_k);
        let mut u_flattened = Vec::with_capacity(k * dim);

        for i in 0..k {
            let row = v_t.row(i);
            for &val in row.iter() {
                u_flattened.push(val as f64);
            }
        }

        Ok(SvdResult {
            u: u_flattened,
            s: s[..k].to_vec(),
            k: k as u32,
            dim: dim as u32,
        })
    }

    /// 高性能 Gram-Schmidt 正交投影
    pub fn compute_orthogonal_projection(
        &self,
        vector: Vec<u8>,
        flattened_tags: Vec<u8>,
        n_tags: u32,
    ) -> PyResult<OrthogonalProjectionResult> {
        let dim = self.dimensions as usize;
        let n = n_tags as usize;

        let query: &[f32] = unsafe {
            std::slice::from_raw_parts(vector.as_ptr() as *const f32, vector.len() / 4)
        };
        let tags_slice: &[f32] = unsafe {
            std::slice::from_raw_parts(flattened_tags.as_ptr() as *const f32, flattened_tags.len() / 4)
        };

        if query.len() != dim || tags_slice.len() != n * dim {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Dimension mismatch".to_string()));
        }

        let mut basis: Vec<Vec<f64>> = Vec::with_capacity(n);
        let mut basis_coefficients = vec![0.0; n];
        let mut projection = vec![0.0; dim];

        for i in 0..n {
            let start = i * dim;
            let tag_vec = &tags_slice[start..start + dim];
            let mut v: Vec<f64> = tag_vec.iter().map(|&x| x as f64).collect();

            for u in &basis {
                let mut dot = 0.0;
                for d in 0..dim {
                    dot += v[d] * u[d];
                }
                for d in 0..dim {
                    v[d] -= dot * u[d];
                }
            }

            let mut mag_sq = 0.0;
            for d in 0..dim {
                mag_sq += v[d] * v[d];
            }
            let mag = mag_sq.sqrt();

            if mag > 1e-6 {
                for d in 0..dim {
                    v[d] /= mag;
                }

                let mut coeff = 0.0;
                for d in 0..dim {
                    coeff += (query[d] as f64) * v[d];
                }
                basis_coefficients[i] = coeff.abs();

                for d in 0..dim {
                    projection[d] += coeff * v[d];
                }
                basis.push(v);
            }
        }

        let mut residual = vec![0.0; dim];
        for d in 0..dim {
            residual[d] = (query[d] as f64) - projection[d];
        }

        Ok(OrthogonalProjectionResult {
            projection,
            residual,
            basis_coefficients,
        })
    }

    /// 高性能握手分析
    pub fn compute_handshakes(&self, query: Vec<u8>, flattened_tags: Vec<u8>, n_tags: u32) -> PyResult<HandshakeResult> {
        let dim = self.dimensions as usize;
        let n = n_tags as usize;

        let q: &[f32] = unsafe {
            std::slice::from_raw_parts(query.as_ptr() as *const f32, query.len() / 4)
        };
        let tags: &[f32] = unsafe {
            std::slice::from_raw_parts(flattened_tags.as_ptr() as *const f32, flattened_tags.len() / 4)
        };

        let mut magnitudes = Vec::with_capacity(n);
        let mut directions = Vec::with_capacity(n * dim);

        for i in 0..n {
            let start = i * dim;
            let tag_vec = &tags[start..start + dim];
            let mut mag_sq = 0.0;
            let mut delta = vec![0.0; dim];

            for d in 0..dim {
                let diff = (q[d] - tag_vec[d]) as f64;
                delta[d] = diff;
                mag_sq += diff * diff;
            }

            let mag = mag_sq.sqrt();
            magnitudes.push(mag);

            if mag > 1e-9 {
                for d in 0..dim {
                    directions.push(delta[d] / mag);
                }
            } else {
                for _ in 0..dim {
                    directions.push(0.0);
                }
            }
        }

        Ok(HandshakeResult {
            magnitudes,
            directions,
        })
    }

    /// 高性能 EPA 投影
    pub fn project(
        &self,
        vector: Vec<u8>,
        flattened_basis: Vec<u8>,
        mean_vector: Vec<u8>,
        k: u32,
    ) -> PyResult<ProjectResult> {
        let dim = self.dimensions as usize;
        let k = k as usize;

        let vec: &[f32] = unsafe {
            std::slice::from_raw_parts(vector.as_ptr() as *const f32, vector.len() / 4)
        };
        let basis_slice: &[f32] = unsafe {
            std::slice::from_raw_parts(flattened_basis.as_ptr() as *const f32, flattened_basis.len() / 4)
        };
        let mean: &[f32] = unsafe {
            std::slice::from_raw_parts(mean_vector.as_ptr() as *const f32, mean_vector.len() / 4)
        };

        if vec.len() != dim || basis_slice.len() != k * dim || mean.len() != dim {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Dimension mismatch".to_string()));
        }

        let mut centered = vec![0.0; dim];
        for d in 0..dim {
            centered[d] = (vec[d] - mean[d]) as f64;
        }

        let mut projections = vec![0.0; k];
        let mut total_energy = 0.0;

        for i in 0..k {
            let start = i * dim;
            let b = &basis_slice[start..start + dim];
            let mut dot = 0.0;
            for d in 0..dim {
                dot += centered[d] * (b[d] as f64);
            }
            projections[i] = dot;
            total_energy += dot * dot;
        }

        let mut probabilities = vec![0.0; k];
        let mut entropy = 0.0;

        if total_energy > 1e-12 {
            for i in 0..k {
                let p = (projections[i] * projections[i]) / total_energy;
                probabilities[i] = p;
                if p > 1e-9 {
                    entropy -= p * p.log2();
                }
            }
        }

        Ok(ProjectResult {
            projections,
            probabilities,
            entropy,
            total_energy,
        })
    }
}

/// Python 模块定义
#[pymodule]
fn vector_db(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<VexusIndex>()?;
    m.add_class::<SearchResult>()?;
    m.add_class::<SvdResult>()?;
    m.add_class::<OrthogonalProjectionResult>()?;
    m.add_class::<HandshakeResult>()?;
    m.add_class::<ProjectResult>()?;
    m.add_class::<VexusStats>()?;
    Ok(())
}
