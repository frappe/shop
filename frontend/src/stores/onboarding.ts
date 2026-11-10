import { call } from 'frappe-ui'

export interface GatewayAccount {
	name: string
	payment_gateway: string
	currency: string
	is_default: 0 | 1
}

export interface OnboardingState {
	onboarding_complete: boolean
	store_name: string | null
	store_logo: string | null
	has_sample_products: boolean
	enable_cod: 0 | 1
	payment_gateways: string[]
	gateway_accounts: GatewayAccount[]
}

let statePromise: Promise<OnboardingState> | null = null

export function fetchOnboardingState(refresh = false) {
	if (!statePromise || refresh) {
		statePromise = call('shop.api.onboarding.get_state')
	}
	return statePromise
}
