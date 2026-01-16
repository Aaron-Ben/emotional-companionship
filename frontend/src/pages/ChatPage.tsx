/** Main chat page component - RPG dialogue style */

import React, { useState } from 'react';
import { RPGChatPanel } from '../components/conversation';
import { CharacterInfoModal } from '../components/character';
import { ChatHistory } from '../components/history';
import { FloatingActionButton } from '../components/ui';
import { useChat } from '../hooks/useChat';
import { useCharacter } from '../hooks/useCharacter';
import backgroundImage from '/background/image.png';

interface ChatPageProps {
  onBack: () => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({ onBack }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
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
        onClick={() => setShowHistory(true)}
        icon="💬"
        ariaLabel="对话历史"
        position="bottom-right"
        index={0}
      />
      <FloatingActionButton
        onClick={() => setShowInfo(true)}
        icon="⭐"
        ariaLabel="角色信息"
        position="bottom-right"
        index={1}
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
    </div>
  );
};
