export function formatDate(value?: string | null): string {
	const parsed = parse(value)
	if (!parsed) return value || '-'
	return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatDateTime(value?: string | null): string {
	const parsed = parse(value)
	if (!parsed) return value || '-'
	const date = parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
	const time = parsed.toLocaleTimeString('en-GB', { hour: 'numeric', minute: '2-digit' })
	return `${date}, ${time}`
}

export function formatShortDate(value?: string | null): string {
	const parsed = parse(value)
	if (!parsed) return value || '-'
	return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

function parse(value?: string | null): Date | null {
	if (!value) return null
	const parsed = new Date(String(value).replace(' ', 'T'))
	return Number.isNaN(parsed.getTime()) ? null : parsed
}
