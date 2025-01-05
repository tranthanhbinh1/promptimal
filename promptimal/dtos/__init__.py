try:
    from promptimal.dtos.PromptCandidate import PromptCandidate
    from promptimal.dtos.ProgressStep import ProgressStep
    from promptimal.dtos.TokenCount import TokenCount
except ImportError:
    from dtos.PromptCandidate import PromptCandidate
    from dtos.ProgressStep import ProgressStep
    from dtos.TokenCount import TokenCount
