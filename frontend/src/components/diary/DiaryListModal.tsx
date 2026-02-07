/** Diary list modal component */

import React, { useEffect, useState } from 'react';
import { listDiaries, deleteDiary, type DiaryEntry, extractDateFromPath } from '../../services/diaryService';
import { DiaryDeleteModal } from './DiaryDeleteModal';
import { DiaryTimeline } from './DiaryTimeline';

interface DiaryListModalProps {
  isOpen: boolean;
  onClose: () => void;
  diaryName?: string;
  onSelectDiary?: (diary: DiaryEntry) => void;
  onEditDiary?: (diary: DiaryEntry) => void;
}

export const DiaryListModal: React.FC<DiaryListModalProps> = ({
  isOpen,
  onClose,
  diaryName = 'sister_001',
  onSelectDiary,
  onEditDiary
}) => {
  const [diaries, setDiaries] = useState<DiaryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [diaryToDelete, setDiaryToDelete] = useState<DiaryEntry | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadDiaries();
    }
  }, [isOpen, diaryName]);

  const loadDiaries = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listDiaries(diaryName);
      setDiaries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load diaries');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (diary: DiaryEntry, e: React.MouseEvent) => {
    e.stopPropagation();
    setDiaryToDelete(diary);
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    if (!diaryToDelete) return;

    try {
      await deleteDiary(diaryToDelete.path);
      // Reload the list after deletion
      loadDiaries();
      setDiaryToDelete(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete diary');
    }
  };

  const handleEdit = (diary: DiaryEntry, e: React.MouseEvent) => {
    e.stopPropagation();
    onEditDiary?.(diary);
  };

  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <div
          className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-pink-100 via-purple-100 px-6 py-4 border-b border-pink-200">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">妹妹的日记本</h2>
                <p className="text-sm text-gray-600 mt-1">记录与哥哥的点点滴滴～</p>
              </div>
              <button
                onClick={onClose}
                className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
              >
                ×
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="text-center text-gray-500 py-8">
                加载中...
              </div>
            ) : error ? (
              <div className="text-center text-red-500 py-8">
                {error}
              </div>
            ) : diaries.length === 0 ? (
              <div className="text-center text-gray-400 py-8">
                <p className="text-lg mb-2">还没有日记呢～</p>
                <p className="text-sm">妹妹会记录和哥哥的重要时刻</p>
              </div>
            ) : (
              <DiaryTimeline
                diaries={diaries}
                onSelectDiary={onSelectDiary || (() => {})}
                onEditDiary={handleEdit}
                onDeleteDiary={(diary, e) => handleDeleteClick(diary, e)}
              />
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <DiaryDeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleConfirmDelete}
        diaryDate={diaryToDelete ? extractDateFromPath(diaryToDelete.path).toLocaleDateString('zh-CN') : ''}
      />
    </>
  );
};
