<template>
	<div class="space-y-3">
		<div class="flex items-baseline justify-between">
			<span class="text-sm text-ink-gray-6">Stock on hand</span>
			<span class="text-lg font-semibold" :class="stock ? 'text-ink-gray-9' : 'text-ink-red-8'">
				{{ stock }}
			</span>
		</div>

		<template v-if="hasVariants">
			<p class="text-sm text-ink-gray-6">Stock is counted per variant.</p>
			<Button class="w-full" @click="emit('showVariants')">Set stock in Variants</Button>
		</template>

		<template v-else>
			<div class="flex items-center gap-2">
				<FormControl
					v-model="draft"
					type="number"
					aria-label="Stock"
					class="flex-1"
					@keydown.enter="setStock"
				/>
				<Button :disabled="!changed" :loading="saving" @click="setStock">Set stock</Button>
			</div>
			<router-link to="/inventory" class="block text-sm text-ink-gray-5 hover:text-ink-gray-8">
				Manage in Inventory
			</router-link>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, FormControl, call, toast } from 'frappe-ui'

const props = defineProps<{
	itemCode: string
	stock: number
	hasVariants: boolean
}>()

const emit = defineEmits<{ updated: [number]; showVariants: [] }>()

const draft = ref<string | number>(props.stock)
const saving = ref(false)

watch(() => props.stock, (value) => (draft.value = value))

const changed = computed(() => draft.value !== '' && Number(draft.value) !== props.stock)

async function setStock() {
	if (!changed.value) return
	const qty = Number(draft.value)
	if (qty < 0) {
		toast.error('Stock cannot be negative')
		return
	}
	saving.value = true
	try {
		const result = await call('shop.api.inventory.set_stock', { item_code: props.itemCode, qty })
		emit('updated', result.stock)
		toast.success(`Stock set to ${result.stock}`)
	} catch (error) {
		draft.value = props.stock
		toast.error('Could not update stock')
	} finally {
		saving.value = false
	}
}
</script>
