import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../api';

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('downloads the server blob and filename without parsing or reconstructing model values', async () => {
  vi.useFakeTimers();
  const blob = new Blob(['{"value":1.2345678901234567}'], { type: 'application/json' });
  const json = vi.fn();
  const fetch = vi.fn().mockResolvedValue({ ok: true, headers: new Headers({ 'Content-Disposition': 'attachment; filename="person-p-v1-m.valence.json"' }), blob: vi.fn().mockResolvedValue(blob), json });
  vi.stubGlobal('fetch', fetch);
  const createObjectURL = vi.fn().mockReturnValue('blob:exact-model');
  const revokeObjectURL = vi.fn();
  vi.stubGlobal('URL', class extends URL { static createObjectURL = createObjectURL; static revokeObjectURL = revokeObjectURL; });
  let downloaded: { href: string; filename: string } | undefined;
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) { downloaded = { href: this.href, filename: this.download }; });
  await api.exportModelVersion('person id', 'version/id');
  expect(fetch).toHaveBeenCalledWith('/api/persons/person%20id/model-versions/version%2Fid/export');
  expect(createObjectURL).toHaveBeenCalledWith(blob);
  expect(json).not.toHaveBeenCalled();
  expect(downloaded).toEqual({ href: 'blob:exact-model', filename: 'person-p-v1-m.valence.json' });
  expect(document.querySelector('a[download]')).toBeNull();
  expect(revokeObjectURL).not.toHaveBeenCalled();
  vi.runAllTimers();
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:exact-model');
});

it('surfaces server validation failures without downloading', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: 'Review the saved version before export.' }) }));
  await expect(api.exportModelVersion('person', 'version')).rejects.toThrow('Review the saved version before export.');
});
