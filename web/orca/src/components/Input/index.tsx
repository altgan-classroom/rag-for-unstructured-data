import React from "react";

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  input: string;
  loading: boolean;
  handleChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleKeyDown ?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
};

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, prefix, suffix, ...props }, ref) => {
    return (
      <div className="input-wrapper">
        {label && <label>{label}</label>}
        <div className="input-container text-white-a700_01">
          {prefix && <span className="prefix">{prefix}</span>}
          <input
              type="text"
              className="resize-none overflow-hidden min-h-[40px] max-h-[70vh] spotlight_input"
              placeholder={props.loading ? "Generating..." :"Ask me anything..."}
              value={props.input}
              disabled={props.loading}
              onChange={props.handleChange}
              onKeyDown={props.handleKeyDown}
            />
          {suffix && <span className="suffix">{suffix}</span>}
        </div>
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
