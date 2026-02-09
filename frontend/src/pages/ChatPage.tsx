/** Main chat page component - RPG dialogue style with topic sidebar */

import React, { useState, useCallback } from 'react';
import { RPGChatPanel, TraditionalChatPanel } from '../components/conversation';
import { FloatingActionButton, ChatStyleToggle } from '../components/ui';
import { DiaryListModal, DiaryDetailModal, DiaryEditModal } from '../components/diary';
import { TopicSidebar } from '../components/topics';
import { useChat } from '../hooks/useChat';
import { useTopics } from '../hooks/useTopics';
import { useChatStyle } from '../hooks/useChatStyle';
import backgroundImage from '/background/image.png';
import type { DiaryEntry } from '../services/diaryService';
import type { DisplayMessage } from '../types/chat';

const CHARACTER_ID = 'sister_001';

export const ChatPage: React.FC = () => {
  const [showDiaries, setShowDiaries] = useState(false);
  const [showDiaryDetail, setShowDiaryDetail] = useState(false);
  const [showDiaryEdit, setShowDiaryEdit] = useState(false);
  const [selectedDiary, setSelectedDiary] = useState<DiaryEntry | null>(null);
  const [userInput, setUserInput] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleVoiceInputStart = useCallback(() => {
    // Voice input start handling
  }, []);

  const handleVoiceInputEnd = useCallback(() => {
    // Voice input end handling
  }, []);

  // Topic management
  const {
    topics,
    currentTopicId,
    characterUuid,
    loading: topicsLoading,
    createNewTopic,
    selectTopic,
    deleteTopicById: deleteTopic,
    refreshTopics,
  } = useTopics({
    characterId: CHARACTER_ID,
    onTopicChange: handleTopicChange,
  });

  // Chat functionality with topic support
  const {
    currentTurn,
    messages,
    loading,
    streamingMessage,
    submitUserMessage,
    clearHistory,
    autoPlayTTS,
    toggleAutoPlayTTS,
    playTTS,
    setMessages: setChatMessages,
  } = useChat({
    characterId: CHARACTER_ID,
    topicId: currentTopicId ?? undefined,
    characterUuid: characterUuid ?? undefined,
  });

  // Chat style management
  const { style: chatStyle, toggleStyle: toggleChatStyle } = useChatStyle();

  // Handle topic selection
  async function handleTopicChange(topicId: number | null, topicMessages: DisplayMessage[]) {
    if (topicId === null) {
      // New topic, clear messages
      clearHistory();
    } else {
      // Load topic messages
      setChatMessages(topicMessages);
    }
  }

  // Create a new topic
  const handleCreateTopic = useCallback(async () => {
    const newTopicId = await createNewTopic();
    if (newTopicId !== null) {
      // New topic created, messages should be cleared
      clearHistory();
    }
  }, [createNewTopic, clearHistory]);

  // Handle topic selection from sidebar
  const handleSelectTopic = useCallback(async (topicId: number) => {
    await selectTopic(topicId);
  }, [selectTopic]);

  // Handle topic deletion
  const handleDeleteTopic = useCallback(async (topicId: number) => {
    await deleteTopic(topicId);
    // Refresh topics after deletion
    await refreshTopics();
  }, [deleteTopic, refreshTopics]);

  const handleSend = () => {
    if (userInput.trim()) {
      submitUserMessage(userInput.trim());
      setUserInput('');
    }
  };

  const handleSendMessage = (content: string) => {
    if (content.trim()) {
      submitUserMessage(content.trim());
    }
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
    <div className="h-screen flex relative">
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

      {/* Topic Sidebar */}
      <TopicSidebar
        topics={topics}
        currentTopicId={currentTopicId}
        loading={topicsLoading}
        collapsed={sidebarCollapsed}
        onSelectTopic={handleSelectTopic}
        onCreateTopic={handleCreateTopic}
        onDeleteTopic={handleDeleteTopic}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Chat Style Toggle Button */}
        <ChatStyleToggle
          currentStyle={chatStyle}
          onToggle={toggleChatStyle}
        />

        {/* Conditional Chat Panel based on style */}
        {chatStyle === 'rpg' ? (
          <>
            {/* Empty space for RPG style */}
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
              placeholder="和妹妹聊聊天吧～"
              onVoiceInputStart={handleVoiceInputStart}
              onVoiceInputEnd={handleVoiceInputEnd}
              onPlayTTS={playTTS}
            />
          </>
        ) : (
          /* Traditional Style Chat Panel - Full height */
          <TraditionalChatPanel
            messages={messages}
            loading={loading}
            streamingMessage={streamingMessage}
            onSendMessage={handleSendMessage}
            onVoiceInputStart={handleVoiceInputStart}
            onVoiceInputEnd={handleVoiceInputEnd}
            placeholder="和妹妹聊聊天吧～"
          />
        )}

        {/* TTS Toggle */}
        <div className="fixed top-[72px] right-4 z-50">
          <button
            onClick={() => toggleAutoPlayTTS(!autoPlayTTS)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-semibold cursor-pointer transition-all duration-300 border-2 shadow-lg hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0 bg-gradient-to-r from-pink-300 to-pink-500 border-pink-200 text-white shadow-pink-300/30 hover:from-pink-500 hover:to-pink-600 hover:shadow-pink-400/40"
            title={autoPlayTTS ? '关闭自动播放' : '开启自动播放'}
            type="button"
          >
            <span className="text-[13px] font-semibold hidden md:inline">
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
      </div>
    </div>
  );
};
