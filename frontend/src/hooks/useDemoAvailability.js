import { useCallback, useEffect, useRef, useState } from 'react';
import { prepareDemo } from '../lib/demo.js';
import { logger } from '../lib/logger.js';

export function useDemoAvailability() {
  const [demoState, setDemoState] = useState({ status: 'checking' });
  const inFlight = useRef(null);

  const ensureDemoReady = useCallback(() => {
    if (inFlight.current) return inFlight.current.promise;
    const controller = new AbortController();
    const promise = prepareDemo(controller.signal, (status) => {
      if (!controller.signal.aborted) setDemoState({ status });
    }).then(() => {
      if (controller.signal.aborted) return false;
      setDemoState({ status: 'ready' });
      return true;
    }).catch((error) => {
      if (!controller.signal.aborted) {
        logger.warn('demo.preparation_failed', { error });
        setDemoState({ status: 'error', reason: error.reason ?? 'startup_failed' });
      }
      return false;
    }).finally(() => {
      if (inFlight.current?.controller === controller) inFlight.current = null;
    });
    inFlight.current = { controller, promise };
    return promise;
  }, []);

  useEffect(() => {
    void ensureDemoReady();
    return () => {
      inFlight.current?.controller.abort();
      inFlight.current = null;
    };
  }, [ensureDemoReady]);

  return { demoState, isDemoReady: demoState.status === 'ready', ensureDemoReady };
}
