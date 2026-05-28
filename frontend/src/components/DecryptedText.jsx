import React, { useState, useEffect } from 'react';

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%&*<>';

export default function DecryptedText({ text, speed = 20, maxIterations = 30, animateOn = 'mount', className = '' }) {
  const [displayText, setDisplayText] = useState('');
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (!text) return;
    
    // If animateOn is 'mount', we trigger it once on text change
    let iteration = 0;
    let interval = null;
    
    const animate = () => {
      setIsAnimating(true);
      clearInterval(interval);
      iteration = 0;
      
      interval = setInterval(() => {
        setDisplayText((prev) => {
          let newText = '';
          for (let i = 0; i < text.length; i++) {
            // If this character has been "decrypted" already
            if (i < iteration) {
              newText += text[i];
            } else if (text[i] === ' ' || text[i] === '\n') {
              // Preserve whitespace
              newText += text[i];
            } else {
              // Otherwise, show a random character
              newText += CHARS[Math.floor(Math.random() * CHARS.length)];
            }
          }
          return newText;
        });

        // Advance decryption (reveal characters faster based on total length)
        iteration += text.length / maxIterations;

        // Finish
        if (iteration >= text.length) {
          clearInterval(interval);
          setDisplayText(text);
          setIsAnimating(false);
        }
      }, speed);
    };

    animate();

    return () => clearInterval(interval);
  }, [text, speed, maxIterations]);

  return (
    <span 
      className={className} 
      style={{ 
        fontFamily: 'var(--mono)',
        fontVariantNumeric: 'tabular-nums',
        opacity: isAnimating ? 0.9 : 1
      }}
    >
      {displayText || text}
    </span>
  );
}
