import * as React from "react"
import { cn } from "../../lib/utils"

interface RadioGroupContextValue {
  value?: string;
  onValueChange?: (value: string) => void;
}

const RadioGroupContext = React.createContext<RadioGroupContextValue>({});

interface RadioGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string;
  onValueChange?: (value: string) => void;
}

const RadioGroup = React.forwardRef<HTMLDivElement, RadioGroupProps>(
  ({ className, value, onValueChange, children, ...props }, ref) => {
    return (
      <RadioGroupContext.Provider value={{ value, onValueChange }}>
        <div
          ref={ref}
          className={cn("space-y-2", className)}
          role="radiogroup"
          {...props}
        >
          {children}
        </div>
      </RadioGroupContext.Provider>
    );
  }
);
RadioGroup.displayName = "RadioGroup"

interface RadioGroupItemProps extends React.InputHTMLAttributes<HTMLInputElement> {
  value: string;
}

const RadioGroupItem = React.forwardRef<HTMLInputElement, RadioGroupItemProps>(
  ({ className, value: itemValue, id, ...props }, ref) => {
    const { value, onValueChange } = React.useContext(RadioGroupContext);
    const isChecked = value === itemValue;
    const inputId = id || `radio-${itemValue}`;

    return (
      <input
        ref={ref}
        type="radio"
        id={inputId}
        value={itemValue}
        checked={isChecked}
        onChange={(e) => {
          if (onValueChange && e.target.checked) {
            onValueChange(itemValue);
          }
        }}
        className={cn(
          "h-4 w-4 border-gray-300 text-blue-600 focus:ring-blue-500",
          className
        )}
        {...props}
      />
    );
  }
);
RadioGroupItem.displayName = "RadioGroupItem"

export { RadioGroup, RadioGroupItem }
