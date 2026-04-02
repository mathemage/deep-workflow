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
    const serverNow = Number(timerElement.dataset.serverNow || "NaN");
    const isRunning = timerElement.dataset.running === "true";

    if (!Number.isFinite(initialRemainingSeconds) || !isRunning) {
      return;
    }

    const clientNowAtStart = Date.now();
    const startupDelaySeconds = Number.isFinite(serverNow)
      ? Math.max(Math.floor((clientNowAtStart - serverNow) / 1000), 0)
      : 0;
    const adjustedInitialRemainingSeconds = Math.max(
      initialRemainingSeconds - startupDelaySeconds,
      0,
    );

    timerElement.textContent = formatDuration(adjustedInitialRemainingSeconds);

    if (adjustedInitialRemainingSeconds <= 0) {
      return;
    }

    const startedAt = clientNowAtStart;

    const tick = () => {
      const elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000);
      const nextRemainingSeconds = Math.max(
        adjustedInitialRemainingSeconds - elapsedSeconds,
        0,
      );
      timerElement.textContent = formatDuration(nextRemainingSeconds);

      if (nextRemainingSeconds === 0) {
        window.clearInterval(intervalId);
      }
    };

    const intervalId = window.setInterval(tick, 1000);
    tick();
  });
});
