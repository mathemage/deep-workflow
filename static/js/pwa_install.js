let deferredInstallPrompt = null;

const installControlsSelector = "[data-pwa-install-controls]";

const isStandalone = () =>
  window.matchMedia("(display-mode: standalone)").matches ||
  window.navigator.standalone === true;

const isIosSafari = () => {
  const userAgent = window.navigator.userAgent;
  const isIosDevice = /iphone|ipad|ipod/i.test(userAgent);
  const isSafariBrowser =
    /safari/i.test(userAgent) && !/crios|fxios|edgios|chrome|android/i.test(userAgent);
  return isIosDevice && isSafariBrowser;
};

const setHidden = (element, isHidden) => {
  if (element) {
    element.hidden = isHidden;
  }
};

const showInstallPrompt = (controls) => {
  const installButton = controls.querySelector("[data-pwa-install-button]");
  const promptCopy = controls.querySelector("[data-pwa-install-prompt]");
  const iosCopy = controls.querySelector("[data-pwa-install-ios]");

  controls.hidden = false;
  setHidden(promptCopy, false);
  setHidden(iosCopy, true);
  setHidden(installButton, false);
};

const showIosHint = (controls) => {
  const installButton = controls.querySelector("[data-pwa-install-button]");
  const promptCopy = controls.querySelector("[data-pwa-install-prompt]");
  const iosCopy = controls.querySelector("[data-pwa-install-ios]");

  controls.hidden = false;
  setHidden(promptCopy, true);
  setHidden(iosCopy, false);
  setHidden(installButton, true);
};

const hideInstallControls = (controls) => {
  const installButton = controls.querySelector("[data-pwa-install-button]");
  const promptCopy = controls.querySelector("[data-pwa-install-prompt]");
  const iosCopy = controls.querySelector("[data-pwa-install-ios]");

  controls.hidden = true;
  setHidden(promptCopy, true);
  setHidden(iosCopy, true);
  setHidden(installButton, true);
};

const syncInstallControls = () => {
  const controls = document.querySelector(installControlsSelector);

  if (!controls || isStandalone()) {
    return;
  }

  if (deferredInstallPrompt) {
    showInstallPrompt(controls);
    return;
  }

  if (isIosSafari()) {
    showIosHint(controls);
  }
};

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  syncInstallControls();
});

window.addEventListener("appinstalled", () => {
  deferredInstallPrompt = null;
  const controls = document.querySelector(installControlsSelector);

  if (controls) {
    hideInstallControls(controls);
  }
});

const registerServiceWorker = () => {
  if (!("serviceWorker" in window.navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    window.navigator.serviceWorker
      .register("/service-worker.js")
      .catch((error) => {
        console.warn("deep-workflow service worker registration failed", error);
      });
  });
};

document.addEventListener("DOMContentLoaded", () => {
  registerServiceWorker();

  const controls = document.querySelector(installControlsSelector);

  if (!controls) {
    return;
  }

  const installButton = controls.querySelector("[data-pwa-install-button]");

  if (installButton) {
    installButton.addEventListener("click", async () => {
      if (!deferredInstallPrompt) {
        return;
      }

      installButton.disabled = true;
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null;
      installButton.disabled = false;
      hideInstallControls(controls);
    });
  }

  syncInstallControls();
});
