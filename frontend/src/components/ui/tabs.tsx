// frontend/src/components/ui/tabs.tsx
import * as React from "react"

interface TabsContextValue {
    value: string
    onValueChange: (value: string) => void
}

const TabsContext = React.createContext<TabsContextValue | undefined>(undefined)

interface TabsProps {
    value?: string
    defaultValue?: string
    onValueChange?: (value: string) => void
    className?: string
    children: React.ReactNode
}

export function Tabs({ value: controlledValue, defaultValue, onValueChange, className, children }: TabsProps) {
    const [uncontrolledValue, setUncontrolledValue] = React.useState(defaultValue || '')

    const value = controlledValue !== undefined ? controlledValue : uncontrolledValue
    const handleValueChange = (newValue: string) => {
        if (controlledValue === undefined) {
            setUncontrolledValue(newValue)
        }
        onValueChange?.(newValue)
    }

    return (
        <TabsContext.Provider value={{ value, onValueChange: handleValueChange }}>
            <div className={className}>
                {children}
            </div>
        </TabsContext.Provider>
    )
}

interface TabsListProps {
    className?: string
    children: React.ReactNode
}

export function TabsList({ className, children }: TabsListProps) {
    return (
        <div className={`inline-flex h-10 items-center justify-center rounded-md p-1 ${className}`}>
            {children}
        </div>
    )
}

interface TabsTriggerProps {
    value: string
    className?: string
    children: React.ReactNode
}

export function TabsTrigger({ value: triggerValue, className, children }: TabsTriggerProps) {
    const context = React.useContext(TabsContext)
    if (!context) throw new Error('TabsTrigger must be used within Tabs')

    const isActive = context.value === triggerValue

    return (
        <button
            onClick={() => context.onValueChange(triggerValue)}
            className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ${className}`}
            data-state={isActive ? 'active' : 'inactive'}
        >
            {children}
        </button>
    )
}

interface TabsContentProps {
    value: string
    className?: string
    children: React.ReactNode
}

export function TabsContent({ value: contentValue, className, children }: TabsContentProps) {
    const context = React.useContext(TabsContext)
    if (!context) throw new Error('TabsContent must be used within Tabs')

    if (context.value !== contentValue) return null

    return (
        <div className={`mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${className}`}>
            {children}
        </div>
    )
}
