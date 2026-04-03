document.addEventListener("DOMContentLoaded", () => {
  const timers = document.querySelectorAll("[data-session-timer]");

  const formatDuration = (totalSeconds) => {
    const clampedSeconds = Math.max(totalSeconds, 0);
    const minutes = Math.floor(clampedSeconds / 60);
    const seconds = clampedSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  };

  const formatAccessibleRemaining = (totalSeconds) => {
    const clampedSeconds = Math.max(totalSeconds, 0);

    if (clampedSeconds === 0) {
      return "Time is up.";
    }

    const minutes = Math.floor(clampedSeconds / 60);
    const seconds = clampedSeconds % 60;
    const parts = [];

    if (minutes > 0) {
      parts.push(`${minutes} minute${minutes === 1 ? "" : "s"}`);
    }
    if (seconds > 0) {
      parts.push(`${seconds} second${seconds === 1 ? "" : "s"}`);
    }

    return `${parts.join(" ")} remaining.`;
  };

  timers.forEach((timerElement) => {
    const initialRemainingSeconds = Number(
      timerElement.dataset.remainingSeconds || "0",
    );
    const liveRegionId = timerElement.dataset.liveRegionId || "";
    const liveRegion = liveRegionId
      ? document.getElementById(liveRegionId)
      : null;
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
    let lastAnnouncedRemainingSeconds = null;

    const maybeAnnounceRemaining = (remainingSeconds) => {
      if (!liveRegion || remainingSeconds === lastAnnouncedRemainingSeconds) {
        return;
      }

      const shouldAnnounce =
        remainingSeconds === 0 ||
        remainingSeconds === 10 ||
        remainingSeconds === 30 ||
        remainingSeconds % 60 === 0;

      if (!shouldAnnounce) {
        return;
      }

      liveRegion.textContent = formatAccessibleRemaining(remainingSeconds);
      lastAnnouncedRemainingSeconds = remainingSeconds;
    };

    if (initialDisplayRemainingSeconds <= 0) {
      maybeAnnounceRemaining(initialDisplayRemainingSeconds);
      return;
    }

    const tick = () => {
      const nextRemainingSeconds = getRemainingSeconds();
      timerElement.textContent = formatDuration(nextRemainingSeconds);
      maybeAnnounceRemaining(nextRemainingSeconds);

      if (nextRemainingSeconds === 0) {
        window.clearInterval(intervalId);
      }
    };

    const intervalId = window.setInterval(tick, 1000);
    tick();
  });
});
