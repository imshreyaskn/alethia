import React, { useState, useEffect } from 'react';

const CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';

export default function GlitchLoader({ length = 5, speed = 60, className = '', style = {} }) {
  const [text, setText] = useState(() => {
    let initial = '';
    for (let i = 0; i < length; i++) {
      initial += CHARS[Math.floor(Math.random() * CHARS.length)];
    }
    return initial;
  });

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
        fontSize: '10px',
        fontWeight: 500,
        color: 'var(--t3)', 
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        fontVariantNumeric: 'tabular-nums',
        userSelect: 'none',
        ...style,
      }}
    >
      {text}
    </span>
  );
}
