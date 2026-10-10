export function isDevMode(): boolean {
  return new URLSearchParams(window.location.search).get('dev') === '1'
}
