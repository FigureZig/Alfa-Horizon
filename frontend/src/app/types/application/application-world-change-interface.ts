// Пересмотр заявки по событию реестра: когда и почему, сняты ли подписи
export interface ApplicationWorldChangeInterface {
  at: string
  reasonKey: string
  isSignatureReset: boolean
}
