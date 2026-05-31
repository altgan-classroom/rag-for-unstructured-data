import React from 'react';

const LoadingDots: React.FC = () => {
  return (
    <span className="inline-flex items-center">
      <span className="animate-[bounce_1s_infinite_0ms]">.</span>
      <span className="animate-[bounce_1s_infinite_200ms]">.</span>
      <span className="animate-[bounce_1s_infinite_400ms]">.</span>
    </span>
  );
};

export default LoadingDots; 