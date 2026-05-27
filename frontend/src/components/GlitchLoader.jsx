import React, { useState, useEffect } from 'react';

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%&*<>/\\|{}[]()~';

export default function GlitchLoader({ length = 12, speed = 50, className = '' }) {
  const [text, setText] = useState('');

  useEffect(() => {
    const interval = setInterval(() => {
      let newText = '';
      for (let i = 0; i < length; i++) {
        newText += CHARS[Math.floor(Math.random() * CHARS.length)];
      }
      setText(newText);
    }, speed);

    return () => clearInterval(interval);
  }, [length, speed]);

  return (
    <span 
      className={className}
      style={{ 
        fontFamily: 'var(--mono)', 
        color: 'var(--t2)', 
        letterSpacing: '0.1em',
        textShadow: '1px 0px 0px rgba(255,0,0,0.5), -1px 0px 0px rgba(0,255,255,0.5)'
      }}
    >
      {text}
    </span>
  );
}
