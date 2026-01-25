/** Main chat page component - RPG dialogue style */

import React, { useState } from 'react';
import { RPGChatPanel } from '../components/conversation';
import { CharacterInfoModal } from '../components/character';
import { ChatHistory } from '../components/history';
import { FloatingActionButton } from '../components/ui';
import { DiaryListModal, DiaryDetailModal, DiaryEditModal } from '../components/diary';
import { FutureTimelineModal } from '../components/timeline';
import { useChat } from '../hooks/useChat';
import { useCharacter } from '../hooks/useCharacter';
import backgroundImage from '/background/image.png';
import type { DiaryEntry } from '../services/diaryService';

interface ChatPageProps {
  onBack: () => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({ onBack }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showDiaries, setShowDiaries] = useState(false);
  const [showDiaryDetail, setShowDiaryDetail] = useState(false);
  const [showDiaryEdit, setShowDiaryEdit] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [selectedDiary, setSelectedDiary] = useState<DiaryEntry | null>(null);
  const [userInput, setUserInput] = useState('');

  const {
    currentTurn,
    loading,
    submitUserMessage,
    startNewTurn,
    clearHistory,
    messages,
  } = useChat('sister_001');

  const { character } = useCharacter('sister_001');

  const handleSend = () => {
    if (userInput.trim()) {
      submitUserMessage(userInput.trim());
      setUserInput('');
    }
  };

  const handleClearHistory = () => {
    clearHistory();
    setShowHistory(false);
  };

  const handleSelectDiary = (diary: DiaryEntry) => {
    setSelectedDiary(diary);
    setShowDiaries(false);
    setShowDiaryDetail(true);
  };

  const handleEditDiary = (diary: DiaryEntry) => {
    setSelectedDiary(diary);
    setShowDiaries(false);
    setShowDiaryDetail(false);
    setShowDiaryEdit(true);
  };

  const handleDiaryUpdate = (updatedDiary: DiaryEntry) => {
    setSelectedDiary(updatedDiary);
    // Refresh diary list if needed
  };

  return (
    <div className="h-screen flex flex-col relative">
      {/* Background image */}
      <div
        className="absolute inset-0 -z-10"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }}
      />

      {/* Header */}
      <div className="bg-white/90 backdrop-blur-sm border-b-2 border-pink-200 px-4 py-3 flex items-center gap-3 shadow-sm flex-shrink-0">
        <button
          onClick={onBack}
          className="text-pink-500 hover:text-pink-600 transition-colors p-1 font-medium"
        >
          ← 返回
        </button>
        <div className="flex-1">
          <h2 className="font-semibold text-gray-800">{character?.name || '妹妹'}</h2>
        </div>
      </div>

      {/* Empty space for future content */}
      <div className="flex-1 overflow-y-auto">
        {/* Content can be added here if needed */}
      </div>

      {/* RPG Style Control Panel - Fixed at bottom */}
      <RPGChatPanel
        phase={currentTurn.phase}
        userInput={userInput}
        aiResponse={currentTurn.aiMessage}
        isStreaming={loading}
        onUserInputChange={setUserInput}
        onSend={handleSend}
        onNewTurn={startNewTurn}
        placeholder="和妹妹聊聊天吧～"
      />

      {/* Floating Buttons */}
      <FloatingActionButton
        onClick={() => setShowDiaries(true)}
        icon="📔"
        ariaLabel="日记本"
        position="bottom-right"
        index={0}
      />
      <FloatingActionButton
        onClick={() => setShowHistory(true)}
        icon="💬"
        ariaLabel="对话历史"
        position="bottom-right"
        index={1}
      />
      <FloatingActionButton
        onClick={() => setShowTimeline(true)}
        icon="📅"
        ariaLabel="未来时间线"
        position="bottom-right"
        index={2}
      />
      <FloatingActionButton
        onClick={() => setShowInfo(true)}
        icon="⭐"
        ariaLabel="角色信息"
        position="bottom-right"
        index={3}
      />

      {/* Modals */}
      <CharacterInfoModal
        isOpen={showInfo}
        onClose={() => setShowInfo(false)}
        character={character}
      />
      <ChatHistory
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
        messages={messages}
        onClear={handleClearHistory}
      />
      <DiaryListModal
        isOpen={showDiaries}
        onClose={() => setShowDiaries(false)}
        onSelectDiary={handleSelectDiary}
        onEditDiary={handleEditDiary}
      />
      <DiaryDetailModal
        diary={selectedDiary}
        isOpen={showDiaryDetail}
        onClose={() => setShowDiaryDetail(false)}
      />
      <DiaryEditModal
        isOpen={showDiaryEdit}
        onClose={() => setShowDiaryEdit(false)}
        diary={selectedDiary}
        onUpdate={handleDiaryUpdate}
      />

      {/* Timeline Modal */}
      <FutureTimelineModal
        isOpen={showTimeline}
        onClose={() => setShowTimeline(false)}
        characterId="sister_001"
        userId="user_default"
        daysAhead={30}
      />
    </div>
  );
};
