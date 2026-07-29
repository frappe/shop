import { computed, reactive } from 'vue'
import { call } from 'frappe-ui'

const sessionUser = () => {
	const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
	const user = cookies.get('user_id')
	return user === 'Guest' ? null : user
}

export const session = reactive({
	user: sessionUser(),
	isLoggedIn: computed((): boolean => !!session.user),
	async logout() {
		await call('logout')
		window.location.href = '/login'
	},
})
