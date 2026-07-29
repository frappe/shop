import { call } from 'frappe-ui'

export interface ThemeInfo {
	group: string
	title: string
	description: string
	preview: string | null
	order: number
	pages: string[]
	active: boolean
}

export interface OnboardingState {
	onboarding_complete: boolean
	store_name: string | null
	store_logo: string | null
	active_theme: string | null
	themes: ThemeInfo[]
	has_demo_data: boolean
}

let statePromise: Promise<OnboardingState> | null = null

export function fetchOnboardingState(refresh = false) {
	if (!statePromise || refresh) {
		statePromise = call('shop.api.onboarding.get_state')
	}
	return statePromise
}
