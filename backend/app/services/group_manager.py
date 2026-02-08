import json
import hashlib
import uuid
from pathlib import Path
from typing import Dict, List, Optional
import asyncio
from datetime import datetime

from app.services.embedding import EmbeddingService


class SemanticGroupManager:
    """语义组管理器，用于管理和激活语义分组，增强向量检索"""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.groups: Dict = {}
        self.config: Dict = {}
        self.group_vector_cache: Dict[str, List[float]] = {}  # 向量缓存
        self.save_lock = False  # 保存锁防止并发写入
        self.groups_file_path = Path(__file__).parent / 'semantic_groups.json'
        self.vectors_dir_path = Path(__file__).parent / 'semantic_vectors'
        self.edit_file_path = Path(__file__).parent / 'semantic_groups.edit.json'
        # 异步初始化
        asyncio.create_task(self.initialize())

    async def initialize(self):
        """初始化管理器"""
        self.vectors_dir_path.mkdir(parents=True, exist_ok=True)
        await self.synchronize_from_edit_file()
        await self.load_groups()

    async def synchronize_from_edit_file(self):
        """从.edit.json文件同步配置"""
        try:
            edit_content = self.edit_file_path.read_text(encoding='utf-8')
            edit_data = json.loads(edit_content)
            print('[SemanticGroup] 发现 .edit.json 文件，开始同步...')

            main_data = None
            try:
                main_content = self.groups_file_path.read_text(encoding='utf-8')
                main_data = json.loads(main_content)
            except FileNotFoundError:
                # 主文件不存在，将直接使用 editData 创建
                pass

            # 比较核心数据是否发生变化
            are_different = self._are_core_group_data_different(edit_data, main_data)

            if are_different:
                print('[SemanticGroup] .edit.json 与主文件核心内容不同，正在执行智能合并...')

                # 智能合并：使用 edit.json 的词元，保留 main.json 的 vector_id 等元数据
                new_main_data = self._merge_group_data(edit_data, main_data)

                self.groups_file_path.write_text(
                    json.dumps(new_main_data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                print('[SemanticGroup] 同步完成。')
            else:
                print('[SemanticGroup] .edit.json 与主文件核心内容相同，无需同步。')
        except FileNotFoundError:
            # .edit.json 不存在，什么都不做
            return
        except json.JSONDecodeError as e:
            print(f'[SemanticGroup] 解析 .edit.json 文件时出错，请检查JSON格式: {e}')
        except Exception as e:
            print(f'[SemanticGroup] 同步 .edit.json 文件时出错: {e}')

    def _are_core_group_data_different(self, edit_data: Dict, main_data: Optional[Dict]) -> bool:
        """比较核心数据是否不同"""
        if not main_data:
            return True  # 主文件不存在，肯定不同

        # 比较 config
        if json.dumps(edit_data.get('config', {}), sort_keys=True) != \
           json.dumps(main_data.get('config', {}), sort_keys=True):
            return True

        edit_groups = edit_data.get('groups', {})
        main_groups = main_data.get('groups', {})

        # 检查组名数量是否一致
        if len(edit_groups) != len(main_groups):
            return True

        # 逐个比较组的核心词元
        for group_name in edit_groups:
            if group_name not in main_groups:
                return True  # 组不存在

            edit_group = edit_groups[group_name]
            main_group = main_groups[group_name]

            # 为了稳定比较，对词元数组排序
            edit_words = sorted(edit_group.get('words', []))
            main_words = sorted(main_group.get('words', []))
            if edit_words != main_words:
                return True

            edit_auto_learned = sorted(edit_group.get('auto_learned', []))
            main_auto_learned = sorted(main_group.get('auto_learned', []))
            if edit_auto_learned != main_auto_learned:
                return True

            # 比较权重
            if edit_group.get('weight', 1.0) != main_group.get('weight', 1.0):
                return True

        return False

    def _merge_group_data(self, edit_data: Dict, main_data: Optional[Dict]) -> Dict:
        """合并编辑数据和主数据"""
        if not main_data:
            # 如果主数据不存在，直接返回编辑数据
            return edit_data

        import copy
        new_main_data = copy.deepcopy(main_data)  # 深拷贝主数据作为基础

        # 1. 更新 config
        new_main_data['config'] = edit_data.get('config', {})

        edit_groups = edit_data.get('groups', {})
        new_main_groups = {}

        # 2. 遍历 edit.json 中的组，这是最新的权威来源
        for group_name, edit_group in edit_groups.items():
            existing_group = new_main_data['groups'].get(group_name)

            if existing_group:
                # 组存在，更新词元和权重，保留元数据
                existing_group['words'] = edit_group.get('words', [])
                existing_group['auto_learned'] = edit_group.get('auto_learned', [])
                existing_group['weight'] = edit_group.get('weight', 1.0)
                new_main_groups[group_name] = existing_group
            else:
                # 组是新增的，直接添加
                new_main_groups[group_name] = edit_group

        new_main_data['groups'] = new_main_groups
        return new_main_data

    async def load_groups(self):
        """加载语义组配置"""
        try:
            data = self.groups_file_path.read_text(encoding='utf-8')
            group_data = json.loads(data)
            self.config = group_data.get('config', {})
            self.groups = group_data.get('groups', {})
            print('[SemanticGroup] 语义组配置文件加载成功。')

            needs_resave = False

            # 加载向量并处理旧格式迁移
            for group_name, group in self.groups.items():
                # 迁移逻辑：如果存在 vector 字段但不存在 vector_id
                if 'vector' in group and 'vector_id' not in group:
                    print(f'[SemanticGroup] 检测到旧格式组 "{group_name}"，正在迁移向量...')
                    vector_id = str(uuid.uuid4())
                    vector_path = self.vectors_dir_path / f'{vector_id}.json'
                    vector_path.write_text(json.dumps(group['vector']), encoding='utf-8')

                    self.group_vector_cache[group_name] = group['vector']
                    group['vector_id'] = vector_id
                    del group['vector']  # 从主配置中删除向量
                    needs_resave = True
                elif 'vector_id' in group:
                    try:
                        vector_path = self.vectors_dir_path / f"{group['vector_id']}.json"
                        vector_data = vector_path.read_text(encoding='utf-8')
                        self.group_vector_cache[group_name] = json.loads(vector_data)
                    except FileNotFoundError:
                        print(f'[SemanticGroup] 加载组 "{group_name}" 的向量文件失败 (ID: {group["vector_id"]})')
                        # 如果向量文件丢失，清除ID以便重新计算
                        del group['vector_id']
                        needs_resave = True
                    except Exception as e:
                        print(f'[SemanticGroup] 加载组 "{group_name}" 的向量文件时出错: {e}')
                        del group['vector_id']
                        needs_resave = True

            if needs_resave:
                print('[SemanticGroup] 迁移或清理后，正在重新保存主配置文件...')
                await self.save_groups()

            await self.precompute_group_vectors()
        except FileNotFoundError:
            print('[SemanticGroup] 未找到语义组配置文件，将创建新文件。')
        except Exception as e:
            print(f'[SemanticGroup] 加载语义组配置文件失败: {e}')

    async def save_groups(self):
        """保存语义组配置"""
        if self.save_lock:
            busy_error = RuntimeError('A save operation is already in progress. Please wait a moment and try again.')
            print(f'[SemanticGroup] {busy_error}')
            raise busy_error

        self.save_lock = True
        temp_file_path = self.groups_file_path.with_suffix(f'.json.{uuid.uuid4()}.tmp')

        try:
            # 创建一个不含实际向量数据的副本用于保存
            groups_to_save = json.loads(json.dumps(self.groups))
            for group in groups_to_save.values():
                group.pop('vector', None)  # 确保内存中的临时向量不被保存

            data_to_save = {
                'config': self.config,
                'groups': groups_to_save
            }

            # 1. 写入临时文件
            temp_file_path.write_text(
                json.dumps(data_to_save, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

            # 2. 成功后，重命名临时文件以原子方式替换原文件
            temp_file_path.replace(self.groups_file_path)

            print('[SemanticGroup] 语义组配置已通过原子写入操作更新并保存。')
        except Exception as e:
            print(f'[SemanticGroup] 保存语义组配置文件失败: {e}')
            # 如果出错，尝试清理临时文件
            try:
                temp_file_path.unlink()
            except FileNotFoundError:
                pass
            except Exception as cleanup_error:
                print(f'[SemanticGroup] 清理临时文件 {temp_file_path} 失败: {cleanup_error}')
            raise e
        finally:
            self.save_lock = False

    async def update_groups_data(self, new_data: Dict):
        """更新语义组数据"""
        try:
            old_groups = self.groups.copy()
            self.config = new_data.get('config', self.config)
            self.groups = new_data.get('groups', self.groups)
            print('[SemanticGroup] 接收到来自管理面板的数据，内存已更新。')

            # 清理被删除的组的向量文件
            old_vector_ids = {g.get('vector_id') for g in old_groups.values() if g.get('vector_id')}
            new_vector_ids = {g.get('vector_id') for g in self.groups.values() if g.get('vector_id')}

            for vector_id in old_vector_ids - new_vector_ids:
                try:
                    vector_path = self.vectors_dir_path / f'{vector_id}.json'
                    vector_path.unlink()
                    print(f'[SemanticGroup] 已删除孤立的向量文件: {vector_id}.json')
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f'[SemanticGroup] 删除向量文件 {vector_id}.json 失败: {e}')

            # 重新计算向量并保存所有更改
            await self.precompute_group_vectors()
        except Exception as e:
            print(f'[SemanticGroup] 更新并保存语义组数据失败: {e}')
            raise e

    # ============ 核心功能：组激活 ============
    def detect_and_activate_groups(self, text: str) -> Dict[str, Dict]:
        """检测并激活匹配的语义组"""
        activated_groups = {}

        for group_name, group_data in self.groups.items():
            # 如果 auto_learned 不存在，提供一个空列表作为后备
            auto_learned_words = group_data.get('auto_learned', [])
            all_words = group_data.get('words', []) + auto_learned_words

            matched_words = [w for w in all_words if self.flexible_match(text, w)]

            if matched_words:
                activation_strength = len(matched_words) / len(all_words) if all_words else 0
                activated_groups[group_name] = {
                    'strength': activation_strength,
                    'matched_words': matched_words,
                    'all_words': all_words
                }

                self.update_group_stats(group_name)

        return activated_groups

    @staticmethod
    def flexible_match(text: str, word: str) -> bool:
        """灵活匹配（不区分大小写的包含匹配）"""
        return word.lower() in text.lower()

    def update_group_stats(self, group_name: str):
        """更新组的激活统计"""
        if group_name in self.groups:
            self.groups[group_name]['last_activated'] = datetime.now().isoformat()
            self.groups[group_name]['activation_count'] = \
                self.groups[group_name].get('activation_count', 0) + 1

    # ============ 预计算组向量 ============
    @staticmethod
    def _get_words_hash(words: List[str]) -> Optional[str]:
        """获取词元列表的哈希值"""
        if not words:
            return None
        # 排序以确保顺序无关紧要，并使用稳定的分隔符连接
        sorted_words = sorted(words)
        return hashlib.sha256(json.dumps(sorted_words).encode()).hexdigest()

    async def precompute_group_vectors(self) -> bool:
        """预计算所有组的向量"""
        print('[SemanticGroup] 开始检查并预计算所有组向量...')
        changes_made = False

        for group_name, group_data in self.groups.items():
            auto_learned_words = group_data.get('auto_learned', [])
            all_words = group_data.get('words', []) + auto_learned_words

            if not all_words:
                if 'vector_id' in group_data:
                    print(f'[SemanticGroup] 组 "{group_name}" 词元为空，正在清理旧向量...')
                    try:
                        vector_path = self.vectors_dir_path / f"{group_data['vector_id']}.json"
                        vector_path.unlink()
                        print(f'[SemanticGroup] 已删除向量文件: {group_data["vector_id"]}.json')
                    except FileNotFoundError:
                        pass
                    except Exception as e:
                        print(f'[SemanticGroup] 删除旧向量文件失败: {e}')

                    del group_data['vector_id']
                    group_data.pop('words_hash', None)
                    self.group_vector_cache.pop(group_name, None)
                    changes_made = True
                continue

            current_words_hash = self._get_words_hash(all_words)
            vector_exists = group_name in self.group_vector_cache

            if current_words_hash != group_data.get('words_hash') or not vector_exists:
                if not vector_exists:
                    print(f'[SemanticGroup] 组 "{group_name}" 的向量不存在，开始计算...')
                else:
                    print(f'[SemanticGroup] 组 "{group_name}" 的词元已改变，重新计算向量...')

                group_description = f'{group_name}相关主题：{"、".join(all_words)}'
                vector = await self.embedding_service.get_single_embedding(group_description)

                if vector:
                    # 如果向量之前存在，清理旧文件
                    if 'vector_id' in group_data:
                        try:
                            old_vector_path = self.vectors_dir_path / f"{group_data['vector_id']}.json"
                            old_vector_path.unlink()
                        except FileNotFoundError:
                            pass
                        except Exception as e:
                            print(f'[SemanticGroup] 删除旧向量文件失败: {e}')

                    vector_id = str(uuid.uuid4())
                    vector_path = self.vectors_dir_path / f'{vector_id}.json'
                    vector_path.write_text(json.dumps(vector), encoding='utf-8')

                    self.group_vector_cache[group_name] = vector
                    group_data['vector_id'] = vector_id
                    group_data['words_hash'] = current_words_hash
                    group_data.pop('vector', None)
                    changes_made = True
                    print(f'[SemanticGroup] 已成功计算并保存 "{group_name}" 的新组向量 (ID: {vector_id})')

        if changes_made:
            print('[SemanticGroup] 检测到向量变更，正在保存主配置文件...')
            await self.save_groups()
        else:
            print('[SemanticGroup] 所有组向量均是最新，无需更新。')

        return changes_made

    # ============ 使用预计算向量的快速模式 ============
    async def get_enhanced_vector(
        self,
        original_query: str,
        activated_groups: Dict[str, Dict],
        precomputed_query_vector: Optional[List[float]] = None
    ) -> Optional[List[float]]:
        """获取增强后的查询向量"""
        query_vector = precomputed_query_vector

        if not query_vector:
            print('[SemanticGroup] 未提供预计算向量，正在为原始查询生成新向量...')
            query_vector = await self.embedding_service.get_single_embedding(original_query)

        if not query_vector:
            print('[SemanticGroup] 查询向量无效，无法进行增强。')
            return None

        if not activated_groups:
            return query_vector

        vectors = [query_vector]
        weights = [1.0]  # 原始查询权重

        for group_name, data in activated_groups.items():
            group_vector = self.group_vector_cache.get(group_name)
            if group_vector:
                vectors.append(group_vector)
                # 权重可以根据激活强度和组的全局权重调整
                group_weight = (self.groups[group_name].get('weight', 1.0)) * data['strength']
                weights.append(group_weight)

        if len(vectors) == 1:
            return query_vector  # 没有有效的组向量被添加

        enhanced_vector = self.weighted_average_vectors(vectors, weights)
        print(f'[SemanticGroup] 已将查询向量与 {len(activated_groups)} 个激活的语义组向量进行混合。')
        return enhanced_vector

    @staticmethod
    def weighted_average_vectors(vectors: List[List[float]], weights: List[float]) -> List[float]:
        """计算向量的加权平均"""
        if not vectors:
            return None

        dim = len(vectors[0])
        result = [0.0] * dim

        total_weight = 0.0
        for i, vec in enumerate(vectors):
            if not vec or len(vec) != dim:
                continue  # 跳过无效向量
            weight = weights[i]
            total_weight += weight
            for j in range(dim):
                result[j] += vec[j] * weight

        if total_weight == 0:
            return vectors[0]  # 如果总权重为0，返回原始向量

        for j in range(dim):
            result[j] /= total_weight

        return result
