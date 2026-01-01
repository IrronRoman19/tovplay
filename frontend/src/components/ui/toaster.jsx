import { Toast, ToastClose, ToastDescription, ToastProvider, ToastTitle, ToastViewport } from "@/components/ui/toast";
import { useToast } from "@/components/ui/use-toast";

export function Toaster() {
  const { toasts } = useToast();

  return (
    <ToastProvider>
      {toasts
        .filter(t => t.open !== false)
        .map(({ id, title, description, action, dismissible, ...props }) => {
          return (
            <Toast key={id} {...props}>
              <div className="grid gap-1">
                {title && <ToastTitle>{title}</ToastTitle>}
                {description && <ToastDescription>{description}</ToastDescription>}
              </div>
              {action}
              {dismissible ? <ToastClose /> : null}
            </Toast>
          );
        })}
      <ToastViewport />
    </ToastProvider>
  );
}
