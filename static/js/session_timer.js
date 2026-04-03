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
    const hasServerNow = Number.isFinite(serverNow);
    const serverClientOffsetMilliseconds = hasServerNow
      ? serverNow - clientNowAtStart
      : 0;
    const expiresAtServerTime = hasServerNow
      ? serverNow + initialRemainingSeconds * 1000
      : NaN;

    const getRemainingSeconds = () => {
      if (hasServerNow) {
        const serverAlignedNow = Date.now() + serverClientOffsetMilliseconds;
        return Math.max(
          Math.ceil((expiresAtServerTime - serverAlignedNow) / 1000),
          0,
        );
      }

      const elapsedSeconds = Math.floor((Date.now() - clientNowAtStart) / 1000);
      return Math.max(initialRemainingSeconds - elapsedSeconds, 0);
    };

    const initialDisplayRemainingSeconds = getRemainingSeconds();
    timerElement.textContent = formatDuration(initialDisplayRemainingSeconds);

    if (initialDisplayRemainingSeconds <= 0) {
      return;
    }

    const tick = () => {
      const nextRemainingSeconds = getRemainingSeconds();
      timerElement.textContent = formatDuration(nextRemainingSeconds);

      if (nextRemainingSeconds === 0) {
        window.clearInterval(intervalId);
      }
    };

    const intervalId = window.setInterval(tick, 1000);
    tick();
  });
});
