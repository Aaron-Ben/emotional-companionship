/** Future Timeline Component - Each event is a node, same-day events are vertically connected */

import React, { useState, useEffect } from 'react';
import type { FutureEvent } from '../../types/timeline';
import { getFutureEvents } from '../../services/timelineService';

interface FutureTimelineProps {
  characterId: string;
  userId?: string;
  daysAhead?: number;
  onEventClick?: (event: FutureEvent) => void;
}

interface TimelineNode {
  event: FutureEvent;
  date: string;
  displayDate: string;
  x: number;
  y: number;
  index: number;
  row: number;
  col: number;
  status: 'pending' | 'completed' | 'cancelled';
  isFirstInDate: boolean;
  isLastInDate: boolean;
  eventsInSameDate: number;
  dateIndex: number; // Index within events on the same date
}

export const FutureTimeline: React.FC<FutureTimelineProps> = ({
  characterId,
  userId = 'user_default',
  daysAhead = 30,
  onEventClick,
}) => {
  // 状态颜色映射
  const STATUS_COLORS = {
    pending: '#60a5fa',    // 蓝色
    completed: '#4CAF50',  // 绿色
    cancelled: '#EF4444',  // 红色
  } as const;

  const [nodes, setNodes] = useState<TimelineNode[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  // 计算节点位置（S型布局，同一天的事件垂直排列）
  const calculatePositions = (nodeList: TimelineNode[]) => {
    const datesPerRow = 5; // 每行5个日期
    const dateSpacing = 120; // 日期间距（像素）
    const rowSpacing = 150; // 行间距（像素）
    const eventVerticalSpacing = 45; // 同一天事件之间的垂直间距

    // 按日期分组
    const nodesByDate = new Map<string, TimelineNode[]>();
    nodeList.forEach(node => {
      if (!nodesByDate.has(node.date)) {
        nodesByDate.set(node.date, []);
      }
      nodesByDate.get(node.date)!.push(node);
    });

    // 获取排序后的日期列表
    const sortedDates = Array.from(nodesByDate.keys()).sort();

    return nodeList.map(node => {
      // 找到该日期在所有日期中的索引
      const dateIndex = sortedDates.indexOf(node.date);
      const row = Math.floor(dateIndex / datesPerRow);
      const col = dateIndex % datesPerRow;

      // S型布局：偶数行从左到右，奇数行从右到左
      const actualCol = row % 2 === 0 ? col : datesPerRow - 1 - col;

      // 计算同一日期内的事件位置
      const sameDateNodes = nodesByDate.get(node.date)!;
      const eventIndex = sameDateNodes.findIndex(n => n.event.id === node.event.id);
      const yOffset = eventIndex * eventVerticalSpacing;

      return {
        ...node,
        x: actualCol * dateSpacing + 60,
        y: row * rowSpacing + 60 + yOffset,
        row,
        col: actualCol,
        dateIndex: eventIndex,
      };
    });
  };

  // 格式化日期显示
  const formatDisplayDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const weekday = weekdays[date.getDay()];
    return `${month}月${day}日 ${weekday}`;
  };

  useEffect(() => {
    loadTimeline();
  }, [characterId, daysAhead]);

  const loadTimeline = async () => {
    try {
      const response = await getFutureEvents({
        character_id: characterId,
        user_id: userId,
        days_ahead: daysAhead,
      });

      // 将每个事件创建为一个节点
      const eventNodes: TimelineNode[] = [];

      // 遍历响应，提取所有事件
      for (const [, eventsList] of Object.entries(response)) {
        if (eventsList.length > 0) {
          const firstEvent = eventsList[0];

          eventsList.forEach((event, eventIdx) => {
            eventNodes.push({
              event,
              date: firstEvent.event_date,
              displayDate: formatDisplayDate(firstEvent.event_date),
              x: 0,
              y: 0,
              index: 0,
              row: 0,
              col: 0,
              status: event.status,
              isFirstInDate: eventIdx === 0,
              isLastInDate: eventIdx === eventsList.length - 1,
              eventsInSameDate: eventsList.length,
              dateIndex: eventIdx,
            });
          });
        }
      }

      // 按日期排序，然后按事件ID排序
      eventNodes.sort((a, b) => {
        const dateCompare = a.date.localeCompare(b.date);
        if (dateCompare !== 0) return dateCompare;
        return a.dateIndex - b.dateIndex;
      });

      // 更新索引并计算位置
      const indexedNodes = eventNodes.map((node, idx) => ({
        ...node,
        index: idx,
      }));

      setNodes(calculatePositions(indexedNodes));
    } catch (err) {
      console.error('Failed to load timeline:', err);
    }
  };

  // 生成连接线路径（包含同一天事件的垂直连接）
  const generatePaths = (): { mainPath: string; verticalLines: string[] } => {
    if (nodes.length === 0) return { mainPath: '', verticalLines: [] };

    // 按日期分组
    const nodesByDate = new Map<string, TimelineNode[]>();
    nodes.forEach(node => {
      if (!nodesByDate.has(node.date)) {
        nodesByDate.set(node.date, []);
      }
      nodesByDate.get(node.date)!.push(node);
    });

    const datesPerRow = 5;
    const pathParts: string[] = [];
    const verticalLines: string[] = [];

    // 获取每个日期的第一个节点（用于主路径）
    const firstNodeByDate = Array.from(nodesByDate.entries()).map(([, dateNodes]) => {
      return dateNodes.sort((a, b) => a.dateIndex - b.dateIndex)[0];
    });

    // 排序第一个节点
    firstNodeByDate.sort((a, b) => a.date.localeCompare(b.date));

    const rowCount = Math.ceil(firstNodeByDate.length / datesPerRow);

    for (let row = 0; row < rowCount; row++) {
      const rowFirstNodes = firstNodeByDate.filter((n) => Math.floor(nodes.indexOf(n) / datesPerRow) === row);
      if (rowFirstNodes.length === 0) continue;

      const sortedNodes = row % 2 === 0
        ? rowFirstNodes.sort((a, b) => a.col - b.col)
        : rowFirstNodes.sort((a, b) => b.col - a.col);

      const firstNode = sortedNodes[0];
      const lastNode = sortedNodes[sortedNodes.length - 1];

      if (row === 0) {
        pathParts.push(`M ${firstNode.x} ${firstNode.y}`);
        pathParts.push(`L ${lastNode.x} ${lastNode.y}`);
      } else {
        pathParts.push(`L ${firstNode.x} ${firstNode.y}`);
        pathParts.push(`L ${lastNode.x} ${lastNode.y}`);
      }
    }

    // 生成同一天事件之间的垂直连接线
    for (const [, dateNodes] of nodesByDate) {
      if (dateNodes.length > 1) {
        const sortedDateNodes = [...dateNodes].sort((a, b) => a.dateIndex - b.dateIndex);
        for (let i = 0; i < sortedDateNodes.length - 1; i++) {
          const current = sortedDateNodes[i];
          const next = sortedDateNodes[i + 1];
          verticalLines.push(`M ${current.x} ${current.y + 10} L ${next.x} ${next.y - 10}`);
        }
      }
    }

    return {
      mainPath: pathParts.join(' '),
      verticalLines,
    };
  };

  const handleNodeClick = (node: TimelineNode) => {
    const eventId = node.event.id ?? node.event.title; // Fallback to title if id is undefined
    if (selectedEventId === eventId) {
      setSelectedEventId(null);
    } else {
      setSelectedEventId(eventId);
      if (onEventClick) {
        onEventClick(node.event);
      }
    }
  };

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-gray-400">
        <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <p>暂无未来事件</p>
      </div>
    );
  }

  const datesPerRow = 5;
  const totalDates = new Set(nodes.map(n => n.date)).size;
  const rowCount = Math.ceil(totalDates / datesPerRow);
  const svgWidth = (datesPerRow - 1) * 120 + 120;
  const svgHeight = rowCount * 150 + 100;

  const { mainPath, verticalLines } = generatePaths();

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width={svgWidth}
        height={svgHeight}
        className="mx-auto"
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      >
        {/* 主S型曲线 */}
        <path
          d={mainPath}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.3"
        />

        {/* 同一天事件的垂直连接线 */}
        {verticalLines.map((line, idx) => (
          <path
            key={idx}
            d={line}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray="4,4"
            opacity="0.3"
          />
        ))}

        {/* 节点 */}
        {nodes.map((node) => {
          const eventId = node.event.id ?? node.event.title;
          const isSelected = selectedEventId === eventId;
          const showDateLabel = node.isFirstInDate;

          return (
            <g key={eventId}>
              {/* 日期标签（只在该日期的第一个节点显示） */}
              {showDateLabel && (
                <text
                  x={node.x}
                  y={node.y - 18}
                  textAnchor="middle"
                  className="text-[10px] fill-blue-600 font-semibold"
                >
                  {node.displayDate.split(' ')[0]}
                </text>
              )}

              {/* 节点圆点 */}
              <circle
                cx={node.x}
                cy={node.y}
                r={isSelected ? 11 : 8}
                fill={STATUS_COLORS[node.status]}
                stroke="white"
                strokeWidth="2.5"
                className="cursor-pointer transition-all duration-200 hover:scale-110"
                style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
                onClick={() => handleNodeClick(node)}
              />

              {/* 事件标题（始终显示在节点旁边） */}
              <text
                x={node.x + 15}
                y={node.y + 4}
                textAnchor="start"
                className="text-[11px] fill-gray-700 font-medium"
              >
                {node.event.title}
              </text>

              {/* 事件描述（选中时显示） */}
              {isSelected && node.event.description && (
                <g>
                  {/* 描述框背景 */}
                  <rect
                    x={node.x + 15}
                    y={node.y + 10}
                    width="120"
                    height="35"
                    rx="6"
                    fill="white"
                    stroke="#e5e7eb"
                    strokeWidth="1"
                    filter="drop-shadow(0 2px 4px rgba(0,0,0,0.08))"
                  />
                  <text
                    x={node.x + 75}
                    y={node.y + 32}
                    textAnchor="middle"
                    className="text-[9px] fill-gray-600"
                  >
                    {node.event.description.length > 18
                      ? node.event.description.slice(0, 18) + '...'
                      : node.event.description}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* 图例 */}
      <div className="flex items-center justify-center gap-6 mt-6 text-xs text-gray-500">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full" style={{ backgroundColor: STATUS_COLORS.pending }}></div>
          <span>未完成</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full" style={{ backgroundColor: STATUS_COLORS.completed }}></div>
          <span>已完成</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full" style={{ backgroundColor: STATUS_COLORS.cancelled }}></div>
          <span>已删除</span>
        </div>
      </div>
    </div>
  );
};

export default FutureTimeline;
