import { ApiError } from '../api/types'

/** Mensagens do backend (em inglês) traduzidas para o usuário. */
const KNOWN_DETAILS: Record<string, string> = {
  'Title cannot be empty.': 'Dê um título para a tarefa.',
}

/** Traduz qualquer falha em uma frase que o usuário entende e sabe o que fazer. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (KNOWN_DETAILS[error.message]) return KNOWN_DETAILS[error.message]
    if (error.status === 429) return 'Muitas ações em pouco tempo. Aguarde alguns segundos e tente de novo.'
    if (error.status === 404) return 'Essa tarefa não existe mais. A lista foi atualizada.'
    if (error.status >= 500) return `Algo deu errado no servidor (${error.status}). Tente de novo.`
    return error.message
  }
  // fetch rejeita com TypeError quando não há rede ou o servidor está fora do ar.
  if (error instanceof TypeError) return 'Não foi possível falar com o servidor. Verifique a conexão e tente de novo.'
  return error instanceof Error ? error.message : String(error)
}

export function isNotFound(error: unknown) {
  return error instanceof ApiError && error.status === 404
}
