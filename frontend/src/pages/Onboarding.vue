<template>
	<div class="min-h-screen bg-surface-base">
		<div class="mx-auto max-w-3xl px-6 py-12">
			<div class="mb-10 flex items-center justify-center gap-3">
				<template v-for="(label, index) in stepLabels" :key="label">
					<div class="flex items-center gap-2">
						<span
							class="flex size-6 items-center justify-center rounded-full text-sm"
							:class="
								step > index + 1
									? 'bg-surface-gray-7 text-ink-white'
									: step === index + 1
										? 'bg-surface-gray-7 text-ink-white'
										: 'bg-surface-gray-2 text-ink-gray-5'
							"
						>
							{{ index + 1 }}
						</span>
						<span class="text-base" :class="step === index + 1 ? 'text-ink-gray-9' : 'text-ink-gray-5'">
							{{ label }}
						</span>
					</div>
					<div v-if="index < stepLabels.length - 1" class="h-px w-10 bg-outline-gray-2" />
				</template>
			</div>

			<div v-if="step === 1" class="mx-auto max-w-md">
				<h1 class="text-xl font-semibold text-ink-gray-9">Set up your store</h1>
				<p class="mt-1 text-base text-ink-gray-6">Give your store a name. You can change it later.</p>
				<FormControl
					v-model="storeName"
					class="mt-6"
					label="Store name"
					placeholder="Acme Outfitters"
					required
				/>
				<Button
					class="mt-6 w-full"
					variant="solid"
					:disabled="!storeName.trim()"
					:loading="savingStore"
					@click="saveStore"
				>
					Continue
				</Button>
			</div>

			<div v-else-if="step === 2">
				<h1 class="text-xl font-semibold text-ink-gray-9">Choose a theme</h1>
				<p class="mt-1 text-base text-ink-gray-6">
					Pick a starting point for your storefront. You can switch themes anytime.
				</p>
				<div class="mt-6">
					<ThemeGrid :themes="themes" :applying-group="applyingGroup" @apply="applyTheme" />
				</div>
				<div class="mt-6 flex justify-end">
					<Button variant="solid" :disabled="!!applyingGroup" @click="step = 3">Continue</Button>
				</div>
			</div>

			<div v-else class="mx-auto max-w-md">
				<h1 class="text-xl font-semibold text-ink-gray-9">Sample data</h1>
				<p class="mt-1 text-base text-ink-gray-6">
					Start with a few sample products so your store does not look empty.
				</p>
				<label class="mt-6 flex items-center gap-2 text-base text-ink-gray-8">
					<FormControl v-model="loadDemoData" type="checkbox" />
					Load sample products
				</label>
				<Button class="mt-6 w-full" variant="solid" :loading="finishing" @click="finish">
					Finish
				</Button>
				<div class="mt-4 text-center">
					<a href="/" target="_blank" class="text-base text-ink-gray-6 underline hover:text-ink-gray-8">
						View your store
					</a>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { FormControl, call, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

import ThemeGrid from '@/components/ThemeGrid.vue'
import { fetchOnboardingState, type ThemeInfo } from '@/stores/onboarding'

const router = useRouter()
const stepLabels = ['Store details', 'Theme', 'Sample data']

const step = ref(1)
const storeName = ref('')
const themes = ref<ThemeInfo[]>([])
const applyingGroup = ref<string | null>(null)
const loadDemoData = ref(true)
const savingStore = ref(false)
const finishing = ref(false)

fetchOnboardingState().then((state) => {
	storeName.value = state.store_name || ''
	themes.value = state.themes
})

async function saveStore() {
	savingStore.value = true
	try {
		await call('shop.api.onboarding.setup_store', { store_name: storeName.value.trim() })
		step.value = 2
	} catch (error) {
		toast.error('Could not save store details')
	} finally {
		savingStore.value = false
	}
}

async function applyTheme(group: string) {
	applyingGroup.value = group
	try {
		await call('shop.themes.apply_theme', { group })
		themes.value = themes.value.map((t) => ({ ...t, active: t.group === group }))
	} catch (error) {
		toast.error('Could not apply theme')
	} finally {
		applyingGroup.value = null
	}
}

async function finish() {
	finishing.value = true
	try {
		if (loadDemoData.value) {
			await call('shop.api.onboarding.load_demo_data')
		}
		await call('shop.api.onboarding.complete')
		await fetchOnboardingState(true)
		router.push('/')
	} catch (error) {
		toast.error('Could not complete setup')
	} finally {
		finishing.value = false
	}
}
</script>
