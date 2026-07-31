<template>
	<div v-if="items.length && !allDone" class="rounded-lg border border-outline-gray-1 p-5">
		<h2 class="text-lg font-medium text-ink-gray-9">Setup guide</h2>
		<p class="mt-0.5 text-p-base text-ink-gray-6">
			Use this personalized guide to get your store up and running.
		</p>
		<div class="mt-3 flex items-center gap-3">
			<span class="text-sm text-ink-gray-6">{{ doneCount }} of {{ items.length }} complete</span>
			<div class="h-1 w-36 overflow-hidden rounded-full bg-surface-gray-2">
				<div
					class="h-full rounded-full bg-surface-gray-7 transition-all"
					:style="{ width: `${(doneCount / items.length) * 100}%` }"
				/>
			</div>
		</div>
		<ul class="-mx-2 mt-4 space-y-0.5">
			<li v-for="item in items" :key="item.key">
				<button
					class="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition hover:bg-surface-gray-1"
					@click="open(item)"
				>
					<span
						v-if="item.done"
						class="flex size-5 shrink-0 items-center justify-center rounded-full bg-surface-gray-7 text-ink-white"
					>
						<LucideCheck class="size-3" />
					</span>
					<span v-else class="size-5 shrink-0 rounded-full border border-dashed border-outline-gray-3" />
					<span class="flex-1 text-base" :class="item.done ? 'text-ink-gray-5' : 'text-ink-gray-8'">
						{{ item.label }}
					</span>
					<LucideExternalLink v-if="item.href" class="size-4 text-ink-gray-5" />
					<LucideChevronRight v-else class="size-4 text-ink-gray-5" />
				</button>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import { useRouter } from 'vue-router'

import LucideCheck from '~icons/lucide/check'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucideExternalLink from '~icons/lucide/external-link'

interface GuideItem {
	key: string
	label: string
	done: boolean
	route?: string
	href?: string
}

const router = useRouter()

const guide = createResource({
	url: 'shop.api.admin.get_setup_guide',
	auto: true,
})

const items = computed<GuideItem[]>(() => guide.data || [])
const doneCount = computed(() => items.value.filter((item) => item.done).length)
const allDone = computed(() => doneCount.value === items.value.length)

function open(item: GuideItem) {
	if (item.route) {
		router.push(item.route)
	} else if (item.href) {
		window.open(item.href, '_blank')
	}
}
</script>
