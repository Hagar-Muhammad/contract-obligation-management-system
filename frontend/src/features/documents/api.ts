import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { unwrap } from '../../api/errors'
import type { components } from '../../api/schema'

export type ContractDocument = components['schemas']['DocumentRead']
export type DocumentKind = components['schemas']['DocumentKind']
export type FileType = components['schemas']['FileType']

export const DOCUMENT_KINDS: DocumentKind[] = ['contract', 'amendment', 'annex', 'other']

/** File extensions the browser's file picker should offer for each allowed type (decision D-12). */
export const FILE_TYPE_EXTENSIONS: Record<FileType, string[]> = {
  pdf: ['.pdf'],
  docx: ['.docx'],
  png: ['.png'],
  jpg: ['.jpg', '.jpeg'],
}

const keys = {
  forContract: (contractId: string) => ['contracts', 'documents', contractId] as const,
  limits: ['documents', 'limits'] as const,
}

export function useContractDocuments(contractId: string) {
  return useQuery({
    queryKey: keys.forContract(contractId),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/contracts/{contract_id}/documents', {
          params: { path: { contract_id: contractId } },
        }),
      ),
  })
}

export function useUploadLimits() {
  return useQuery({
    queryKey: keys.limits,
    queryFn: async () => unwrap(await api.GET('/api/v1/documents/limits')),
    staleTime: Infinity,
  })
}

export async function uploadDocument(contractId: string, file: File, kind: DocumentKind) {
  return unwrap(
    await api.POST('/api/v1/contracts/{contract_id}/documents', {
      params: { path: { contract_id: contractId } },
      // The generated type describes the form fields; the request itself is multipart.
      body: { file: file as unknown as string, kind },
      bodySerializer: (body) => {
        const form = new FormData()
        const chosen = body.file as unknown as File
        form.append('file', chosen, chosen.name)
        form.append('kind', String(body.kind))
        return form
      },
    }),
  )
}

export function useUploadDocument(contractId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, kind }: { file: File; kind: DocumentKind }) =>
      uploadDocument(contractId, file, kind),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.forContract(contractId) })
      void queryClient.invalidateQueries({ queryKey: ['contracts', 'activity', contractId] })
    },
  })
}

/** The original file as a Blob. Downloads go through the API (never a public link), with the user's token. */
export async function fetchDocumentFile(document: ContractDocument): Promise<Blob> {
  const blob = unwrap(
    await api.GET('/api/v1/documents/{document_id}/download', {
      params: { path: { document_id: document.id } },
      parseAs: 'blob',
    }),
  ) as unknown as Blob
  return new Blob([blob], { type: document.mime_type })
}

/** Save the original under its own name. */
export async function saveDocument(document: ContractDocument): Promise<void> {
  const url = URL.createObjectURL(await fetchDocumentFile(document))
  const link = globalThis.document.createElement('a')
  link.href = url
  link.download = document.original_filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

/**
 * Show a PDF or image in a new tab. The tab is opened before the download starts, while the click still counts as
 * a user action, so pop-up blockers allow it.
 */
export async function viewDocument(document: ContractDocument): Promise<void> {
  const tab = window.open('', '_blank')
  try {
    const url = URL.createObjectURL(await fetchDocumentFile(document))
    if (tab) tab.location.href = url
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (error) {
    tab?.close()
    throw error
  }
}
