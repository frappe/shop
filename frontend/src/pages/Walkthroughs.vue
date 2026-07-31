<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<template v-if="active">
			<WalkthroughGuide
				:guide="active"
				:preparing="!!preparingKey"
				@back="active = null"
				@prepare="start(active.key)"
			/>
		</template>

		<template v-else>
			<UiPageHeader
				title="Walkthroughs"
				subtitle="Guided flows to try your store the way real shoppers and staff would. Starting one seeds everything the flow needs."
			/>

			<div v-if="personas.error" class="mt-6 flex flex-col items-center gap-3 py-16 text-center">
				<p class="text-p-base text-ink-red-8">Could not load walkthroughs.</p>
				<Button @click="personas.reload()">Try again</Button>
			</div>

			<div v-else-if="!personas.fetched" class="flex justify-center py-16">
				<LoadingIndicator class="size-5 text-ink-gray-5" />
			</div>

			<template v-else>
				<section v-for="group in groups" :key="group.title" class="mt-8">
					<h2 class="text-base font-medium text-ink-gray-8">{{ group.title }}</h2>
					<div class="mt-3 grid gap-4 sm:grid-cols-2">
						<WalkthroughCard
							v-for="guide in group.guides"
							:key="guide.key"
							:guide="guide"
							:preparing="preparingKey === guide.key"
							@start="start(guide.key)"
						/>
					</div>
				</section>
			</template>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { LoadingIndicator, call, createResource, toast } from 'frappe-ui'

import UiPageHeader from '@/components/UiPageHeader.vue'
import WalkthroughCard from '@/components/WalkthroughCard.vue'
import WalkthroughGuide, { type PersonaGuide } from '@/components/WalkthroughGuide.vue'

const active = ref<PersonaGuide | null>(null)
const preparingKey = ref('')

const personas = createResource({
	url: 'shop.api.walkthroughs.get_personas',
	auto: true,
})

const groups = computed(() => {
	const guides: PersonaGuide[] = personas.data || []
	return [
		{ title: 'Shopping flows', guides: guides.filter((guide) => guide.kind === 'shopper') },
		{ title: 'Store management flows', guides: guides.filter((guide) => guide.kind === 'merchant') },
	].filter((group) => group.guides.length)
})

async function start(key: string) {
	preparingKey.value = key
	try {
		active.value = await call('shop.api.walkthroughs.prepare', { persona: key })
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not prepare the walkthrough')
	} finally {
		preparingKey.value = ''
	}
}
</script>
