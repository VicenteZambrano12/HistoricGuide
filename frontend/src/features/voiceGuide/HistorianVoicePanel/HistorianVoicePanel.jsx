import React, { useEffect, useRef } from 'react';
import { useTour } from '../../../store/TourContext';
import { MonumentIllustration } from '../../../components/MonumentIllustration/MonumentIllustration';
import { VoiceOrb } from '../../../components/VoiceOrb/VoiceOrb';
import { ActionPromptChips } from '../ActionPromptChips/ActionPromptChips';
import './HistorianVoicePanel.css';

export function HistorianVoicePanel() {
  const { currentStop, messages } = useTour();
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <aside className="voice-panel">
      <MonumentIllustration stop={currentStop} />
      <VoiceOrb />

      <div className="voice-panel__transcript">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`voice-panel__msg ${
              msg.sender === 'AURELIUS' ? 'voice-panel__msg--ai' : 'voice-panel__msg--user'
            }`}
          >
            <div className="voice-panel__msg-header">
              <span>
                {msg.sender} {msg.tag ? `// ${msg.tag}` : ''}
              </span>
              <span>{msg.timestamp}</span>
            </div>
            <p className="voice-panel__msg-text">{msg.text}</p>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <ActionPromptChips />
    </aside>
  );
}
