import { SendHorizontal } from "lucide-react";
import { useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const MAX_HEIGHT = 160;

export default function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl border bg-panel/80 p-2 shadow-card backdrop-blur transition",
          "border-line focus-within:border-brand-400/60 focus-within:shadow-glow"
        )}
      >
        <label htmlFor="chat-input" className="sr-only">
          Ask a question about your documents
        </label>
        <textarea
          id="chat-input"
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? "Ask something about your documents..."}
          className="max-h-40 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-content placeholder:text-subtle focus:outline-none disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Send message"
        >
          <SendHorizontal size={18} aria-hidden />
        </button>
      </div>
      <p className="mt-1.5 px-2 text-[11px] text-subtle">
        Answers are grounded only in your uploaded documents. Press Enter to send, Shift+Enter for a new line.
      </p>
    </form>
  );
}
