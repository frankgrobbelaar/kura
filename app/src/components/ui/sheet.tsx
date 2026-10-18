import { X } from "lucide-react";
import { Dialog } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

// Adapted from shadcn/ui's sheet (MIT, see LICENSE-shadcn.txt), restyled to Cinema: a panel that
// comes in from the window's right side, below the title bar, over the page it tells more of,
// which dims behind it. Escape, the cross or a click beside it closes it.

export const Sheet = Dialog.Root;

export function SheetContent({
  className,
  children,
  title,
  description,
  ...props
}: ComponentProps<typeof Dialog.Content> & {
  /** What it's about: its heading, which names it for screen readers too. */
  title: ReactNode;
  /** A line under the heading ("TV series · 2019"), or nothing. */
  description?: ReactNode;
}) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-x-0 top-13 bottom-0 z-40 animate-fade-in bg-window/70" />
      <Dialog.Content
        data-slot="sheet"
        className={cn(
          "fixed top-15 right-3 bottom-3 z-40 flex w-[min(30rem,calc(100vw-1.5rem))] animate-sheet-in flex-col overflow-hidden rounded-28 border border-edge bg-dialog shadow-dialog outline-none",
          className,
        )}
        {...props}
      >
        <header className="flex items-start gap-3 border-rule border-b px-6 pt-5 pb-4">
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <Dialog.Title className="font-extrabold text-18 leading-tight">{title}</Dialog.Title>
            {description ? (
              <Dialog.Description className="text-13 text-fg-muted">
                {description}
              </Dialog.Description>
            ) : (
              <Dialog.Description className="sr-only">{title}</Dialog.Description>
            )}
          </div>
          <Dialog.Close
            aria-label="Close"
            className="press -mt-1 -mr-2 inline-flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full text-fg-muted hover:bg-tint/8 hover:text-fg"
          >
            <X size={18} aria-hidden="true" />
          </Dialog.Close>
        </header>
        <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-6 py-5">
          {children}
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  );
}
