import type { ApplicationInterface } from '@/app/types/application/application-interface'
import type { ApplicationTaskInterface } from '@/app/types/application/application-task-interface'

/** Заявка, по которой банк ждёт голос участника: задача и сама заявка с ходом голосования. */
export interface VoteItemInterface {
  task: ApplicationTaskInterface
  application: ApplicationInterface
}
