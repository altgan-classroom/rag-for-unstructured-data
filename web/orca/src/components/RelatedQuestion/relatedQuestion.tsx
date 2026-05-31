const RelatedQuestion = ({ question, onQuestionClick }: {question: string, onQuestionClick : (question: string)=> void}) => (
    <div 
      className="mt-4 p-3 bg-slate-300 hover:bg-white max-w-[90%] rounded-lg shadow-md transition-all duration-300 ease-in-out cursor-pointer flex items-center space-x-3"
      onClick={() => onQuestionClick(question)}
    >
      <svg 
        className="w-6 h-6 flex-shrink-0" 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24" 
        xmlns="http://www.w3.org/2000/svg"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
        />
      </svg>
      <span className="text-sm font-medium text-slate-950">{question}</span>
    </div>
  );

export default RelatedQuestion;