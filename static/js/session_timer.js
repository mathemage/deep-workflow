document.addEventListener("DOMContentLoaded", () => {
  const timers = document.querySelectorAll("[data-session-timer]");

  const formatDuration = (totalSeconds) => {
    const clampedSeconds = Math.max(totalSeconds, 0);
    const minutes = Math.floor(clampedSeconds / 60);
    const seconds = clampedSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  };

  timers.forEach((timerElement) => {
    const initialRemainingSeconds = Number(
      timerElement.dataset.remainingSeconds || "0",
    );
    const isRunning = timerElement.dataset.running === "true";

    if (!Number.isFinite(initialRemainingSeconds) || !isRunning) {
      return;
    }

    const startedAt = Date.now();
    let intervalId = null;

    const tick = () => {
      const elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000);
      const nextRemainingSeconds = Math.max(
        initialRemainingSeconds - elapsedSeconds,
        0,
      );
      timerElement.textContent = formatDuration(nextRemainingSeconds);

      if (nextRemainingSeconds === 0) {
        window.clearInterval(intervalId);
      }
    };

    tick();
    intervalId = window.setInterval(tick, 1000);
  });
});
