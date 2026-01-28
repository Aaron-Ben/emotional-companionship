/** Main chat page component - RPG dialogue style */

import React, { useState, useCallback } from 'react';
import { RPGChatPanel } from '../components/conversation';
import { ChatHistory } from '../components/history';
import { FloatingActionButton } from '../components/ui';
import { DiaryListModal, DiaryDetailModal, DiaryEditModal } from '../components/diary';
import { FutureTimelineModal } from '../components/timeline';
import { useChat } from '../hooks/useChat';
import backgroundImage from '/background/image.png';
import type { DiaryEntry } from '../services/diaryService';

export const ChatPage: React.FC = () => {
  const [showHistory, setShowHistory] = useState(false);
  const [showDiaries, setShowDiaries] = useState(false);
  const [showDiaryDetail, setShowDiaryDetail] = useState(false);
  const [showDiaryEdit, setShowDiaryEdit] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [selectedDiary, setSelectedDiary] = useState<DiaryEntry | null>(null);
  const [userInput, setUserInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  const handleVoiceInputStart = useCallback(() => {
    setIsRecording(true);
  }, []);

  const handleVoiceInputEnd = useCallback(() => {
    setIsRecording(false);
  }, []);

  const {
    currentTurn,
    loading,
    submitUserMessage,
    startNewTurn,
    clearHistory,
    messages,
    autoPlayTTS,
    toggleAutoPlayTTS,
    playTTS,
  } = useChat('sister_001');

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
        onVoiceInputStart={handleVoiceInputStart}
        onVoiceInputEnd={handleVoiceInputEnd}
        onPlayTTS={playTTS}
      />

      {/* TTS Toggle */}
      <div className="fixed bottom-4 left-4 z-50">
        <button
          onClick={() => toggleAutoPlayTTS(!autoPlayTTS)}
          className={`px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 transition-all ${
            autoPlayTTS
              ? 'bg-purple-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
          title={autoPlayTTS ? '关闭自动播放' : '开启自动播放'}
        >
          <span>{autoPlayTTS ? '🔊' : '🔇'}</span>
          <span className="text-sm font-medium">
            {autoPlayTTS ? '语音开启' : '语音关闭'}
          </span>
        </button>
      </div>

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

      {/* Modals */}
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
