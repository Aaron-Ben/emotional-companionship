#!/usr/bin/env python3
"""
Vexus-Lite Python 测试文件
"""

import struct
import os
from vector_db import VexusIndex

print('🧪 Testing Vexus-Lite (PyO3)...\n')

try:
    # 测试1: 创建索引
    print('Test 1: Creating new index...')
    vexus = VexusIndex(dim=128, capacity=1000)
    print('✅ Index created successfully\n')

    # 测试2: 添加向量
    print('Test 2: Adding vectors...')

    # 生成3个128维的随机向量
    import random
    vectors = []
    for _ in range(3 * 128):
        vectors.append(random.random())

    # 转换为字节 (f32数组)
    vector_bytes = struct.pack(f'{len(vectors)}f', *vectors)

    # 批量添加
    ids = [1, 2, 3]
    vexus.add_batch(ids, vector_bytes)
    print('✅ Vectors added successfully\n')

    # 测试3: 搜索
    print('Test 3: Searching...')
    query = [random.random() for _ in range(128)]
    query_bytes = struct.pack(f'{len(query)}f', *query)

    results = vexus.search(query_bytes, 2)
    print('✅ Search results:')
    for r in results:
        print(f'   - ID: {r.id}, Score: {r.score:.4f}')
    print()

    # 测试4: 统计
    print('Test 4: Getting stats...')
    stats = vexus.stats()
    print('✅ Stats:')
    print(f'   - Total vectors: {stats.total_vectors}')
    print(f'   - Dimensions: {stats.dimensions}')
    print(f'   - Capacity: {stats.capacity}')
    print(f'   - Memory usage: {stats.memory_usage}')
    print()

    # 测试5: 保存
    print('Test 5: Saving index...')
    vexus.save('./test_index.usearch')
    print('✅ Index saved successfully\n')

    # 测试6: 加载
    print('Test 6: Loading index...')
    vexus2 = VexusIndex.load(dim=128, capacity=1000, index_path='./test_index.usearch')
    stats2 = vexus2.stats()
    print('✅ Index loaded successfully')
    print(f'   Loaded stats: {stats2.total_vectors} vectors, {stats2.dimensions} dimensions')
    print()

    # 测试7: 单个添加
    print('Test 7: Adding single vector...')
    single_vector = [random.random() for _ in range(128)]
    single_bytes = struct.pack(f'{len(single_vector)}f', *single_vector)
    vexus.add(4, single_bytes)
    print('✅ Single vector added\n')

    # 测试8: 删除
    print('Test 8: Removing vector...')
    vexus.remove(1)
    print('✅ Vector removed\n')

    # 最终统计
    print('Final stats:')
    final_stats = vexus.stats()
    print(f'   Total vectors: {final_stats.total_vectors}')
    print()

    print('🎉 All tests passed!')

    # 清理测试文件
    try:
        os.remove('./test_index.usearch')
        print('🧹 Cleaned up test files')
    except:
        pass

except Exception as e:
    print(f'❌ Test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
