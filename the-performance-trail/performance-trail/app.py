import os
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

SYSTEM_PROMPT = """You are a writing assistant embedded in a text-adventure game that a manager uses to draft performance reviews. The manager will give you rambling, informal, possibly disorganized, dictation-style notes about a direct report, written in response to a specific review question. You may also be given the direct report's own self-review answer to that same question, as context only.

Turn the manager's notes into a clear, professional, well-written performance review answer (roughly 2-5 sentences) suitable for pasting directly into an HR review form. Write about the employee in the third person, in a constructive, professional HR tone.

Rules:
- Preserve the manager's actual opinions, facts, and specific examples faithfully.
- Do not invent achievements, numbers, project names, or claims that are not present in the manager's notes.
- Do not simply repeat the direct report's self-review; the output should reflect the manager's own perspective.
- Do not mention this game, dictation, notes, or the process itself in the output.
- Return ONLY the finished review answer text, with no preamble, labels, or quotation marks."""


def mock_draft(notes, previous_draft, tone_instruction):
    if previous_draft and tone_instruction:
        return f"[MOCK TONE TWEAK: {tone_instruction}] {previous_draft[:300]}"
    return f"[MOCK DRAFT] Based on the manager's notes: {notes[:300]}"


def build_user_message(question, self_review, notes, previous_draft, tone_instruction):
    if previous_draft and tone_instruction:
        return (
            f"Review question:\n{question}\n\n"
            f"Previous draft:\n{previous_draft}\n\n"
            f"Tone instruction: {tone_instruction}\n"
            f"Please revise accordingly, keeping the same faithfulness rules."
        )
    # Fresh draft
    parts = [f"Review question:\n{question}"]
    if self_review:
        parts.append(f"Direct report's own self-review answer (context only):\n{self_review}")
    parts.append(f"Manager's rambling notes:\n{notes}")
    return "\n\n".join(parts)


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/draft', methods=['POST'])
def api_draft():
    data = request.get_json(silent=True) or {}

    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': 'Missing required field: question'}), 400

    self_review = data.get('self_review', '') or ''
    notes = data.get('notes', '') or ''
    previous_draft = data.get('previous_draft') or None
    tone_instruction = data.get('tone_instruction') or None

    use_mock = os.environ.get('MOCK', '').lower() in ('1', 'true')

    if use_mock:
        draft = mock_draft(notes, previous_draft, tone_instruction)
        return jsonify({'draft': draft})

    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY not set. Run with MOCK=1 to test without a key.'}), 500

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        user_message = build_user_message(question, self_review, notes, previous_draft, tone_instruction)
        message = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_message}],
        )
        draft = message.content[0].text
        return jsonify({'draft': draft})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
