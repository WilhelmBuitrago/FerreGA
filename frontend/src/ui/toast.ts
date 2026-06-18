type ToastLevel = "info" | "error" | "success";

let container: HTMLDivElement | null = null;

const ensureContainer = () => {
  if (container) return container;
  container = document.createElement("div");
  container.className = "toast-container";
  document.body.appendChild(container);
  return container;
};

const showToast = (message: string, level: ToastLevel) => {
  const root = ensureContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${level}`;
  toast.textContent = message;
  root.appendChild(toast);
  setTimeout(() => {
    toast.remove();
    if (root.childElementCount === 0) {
      root.remove();
      container = null;
    }
  }, 4000);
};

export const notifyError = (message: string) => showToast(message, "error");
export const notifyInfo = (message: string) => showToast(message, "info");
export const notifySuccess = (message: string) => showToast(message, "success");
