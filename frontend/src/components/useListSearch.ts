import { useEffect, useState } from 'react'

/**
 * State for a paginated, searchable list: the search box text, the trimmed query to send (updated once typing
 * pauses, not on every keystroke) and the current page, which goes back to 1 whenever the query changes.
 */
export function useListSearch(initial = '', delayMs = 300) {
  const [search, setSearch] = useState(initial)
  const [query, setQuery] = useState(initial.trim())
  const [page, setPage] = useState(1)

  useEffect(() => {
    const timer = setTimeout(() => setQuery(search.trim()), delayMs)
    return () => clearTimeout(timer)
  }, [search, delayMs])

  // Adjust state during render (not in an effect) so the new query never fetches a stale page.
  const [pagedQuery, setPagedQuery] = useState(query)
  if (pagedQuery !== query) {
    setPagedQuery(query)
    setPage(1)
  }

  return { search, setSearch, query, page, setPage }
}
