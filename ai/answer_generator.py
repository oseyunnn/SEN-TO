from ai.prompts import FALLBACK


class MockAnswerGenerator:
    def generate(self, query, senator, context, style):
        if not context:
            return FALLBACK
        # Style affects presentation only. Every factual/content sentence comes from context.
        opening = f"A guide to reviewing {senator['name']}’s public record."
        paragraphs = [doc["content"] for doc in context]
        if style.get("presentation") == "numbered":
            paragraphs = [f"{i}. {paragraph}" for i, paragraph in enumerate(paragraphs, 1)]
        return opening + "\n\n" + "\n\n".join(paragraphs) + "\n\nNo senator-specific fact is confirmed by this sample answer."
