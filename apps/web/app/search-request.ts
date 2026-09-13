export type SearchTicket = { signal: AbortSignal; isCurrent: () => boolean; finish: () => void };

// One active search across address, location and area modes. Aborting fetch
// cannot retract an already-sent request, but stale callbacks cannot render or
// send a late geolocation fix after the user has left that mode.
export function createSearchRequests(timeoutMs = 15_000) {
  let current: AbortController | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancel() {
    current?.abort(); current = null;
    clearTimeout(timer); timer = undefined;
  }
  return {
    cancel,
    begin(onTimeout: () => void): SearchTicket {
      cancel();
      const controller = new AbortController(); current = controller;
      const isCurrent = () => current === controller && !controller.signal.aborted;
      timer = setTimeout(() => { if (isCurrent()) { cancel(); onTimeout(); } }, timeoutMs);
      return { signal: controller.signal, isCurrent, finish: () => {
        if (isCurrent()) { clearTimeout(timer); timer = undefined; current = null; }
      } };
    },
  };
}
