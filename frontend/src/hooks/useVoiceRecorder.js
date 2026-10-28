import { useCallback, useEffect, useRef, useState } from 'react';

export function useVoiceRecorder(onRecorded, onActiveChange) {
  const sessionRef = useRef(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);

  const cancel = useCallback(() => {
    const session = sessionRef.current;
    if (!session) return;
    sessionRef.current = null;
    if (session?.recorder && session.recorder.state !== 'inactive') {
      session.recorder.stop();
    }
    session?.stream?.getTracks().forEach((track) => track.stop());
    onActiveChange(false);
  }, [onActiveChange]);

  useEffect(() => cancel, [cancel]);

  const start = useCallback(async () => {
    if (sessionRef.current) return;
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError({ key: 'recordingUnsupported' });
      return;
    }

    const session = { stream: null, recorder: null };
    sessionRef.current = session;
    onActiveChange(true);
    setStatus('requesting');

    const fail = (message) => {
      if (sessionRef.current !== session) return;
      cancel();
      setStatus('idle');
      setError(message);
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (sessionRef.current !== session) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      session.stream = stream;
      const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4']
        .find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      session.recorder = recorder;
      if (!recorder.mimeType.startsWith('audio/')) {
        fail({ key: 'recordingFormatError' });
        return;
      }

      const chunks = [];
      let size = 0;
      recorder.ondataavailable = ({ data }) => {
        if (sessionRef.current !== session) return;
        size += data.size;
        if (size > 14_000_000) {
          fail({ key: 'recordingTooLarge' });
          return;
        }
        if (data.size) chunks.push(data);
      };
      recorder.onerror = () => fail({ key: 'recordingFailed' });
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        if (sessionRef.current !== session) return;
        sessionRef.current = null;
        onActiveChange(false);
        setStatus('idle');
        if (!size) {
          setError({ key: 'recordingEmpty' });
          return;
        }
        const extension = recorder.mimeType.includes('mp4') ? 'm4a'
          : recorder.mimeType.includes('ogg') ? 'ogg' : 'webm';
        onRecorded(new File(chunks, `voice-message.${extension}`, {
          type: recorder.mimeType.split(';')[0]
        }));
      };
      recorder.start(1000);
      setStatus('recording');
    } catch (recordingError) {
      fail({ key: 'microphoneError', values: { detail: recordingError.message } });
    }
  }, [cancel, onRecorded, onActiveChange]);

  const stop = useCallback(() => {
    const recorder = sessionRef.current?.recorder;
    if (!recorder || recorder.state === 'inactive') return;
    setStatus('stopping');
    recorder.stop();
  }, []);

  return { status, error, start, stop };
}
