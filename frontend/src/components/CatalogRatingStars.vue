<template>
	<div class="flex items-center gap-0.5" :title="`${rating} out of 5`">
		<LucideStar
			v-for="star in 5"
			:key="star"
			class="size-3.5"
			:class="star <= Math.round(rating) ? 'fill-yellow-400 text-yellow-400' : 'text-outline-gray-2'"
		/>
	</div>
</template>

<script setup lang="ts">
import LucideStar from '~icons/lucide/star'

defineProps<{ rating: number }>()
</script>
