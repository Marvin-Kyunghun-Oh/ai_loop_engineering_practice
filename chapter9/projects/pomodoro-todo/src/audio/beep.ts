// 짧은 사인파 비프. 실패해도 던지지 않는다(PRD 8절).
export function playBeep(): void {
  try {
    const w = globalThis as unknown as {
      AudioContext?: new () => AudioContext
      webkitAudioContext?: new () => AudioContext
    }
    const Ctor = w.AudioContext ?? w.webkitAudioContext
    if (!Ctor) return
    const ctx = new Ctor()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = 880
    gain.gain.value = 0.2
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.onended = () => {
      try {
        void ctx.close()
      } catch {
        // 무시
      }
    }
    osc.start()
    osc.stop(ctx.currentTime + 0.3)
  } catch {
    // 알림음 실패는 무시한다
  }
}
