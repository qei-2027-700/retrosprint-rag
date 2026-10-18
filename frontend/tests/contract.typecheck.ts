import { createApiClient } from '../app/api/client'
const client = createApiClient('http://localhost:8000')

async function contract() {
  // @ts-expect-error unknown API path
  await client.GET('/unknown')
  // @ts-expect-error required message is missing
  await client.POST('/api/v1/dev/echo', { body: {} })
  // @ts-expect-error message must be a string
  await client.POST('/api/v1/dev/echo', { body: { message: 123 } })
  const { data, error } = await client.POST('/api/v1/dev/echo', { body: { message: 'test' } })
  if (data) {
    const message: string = data.message
    // @ts-expect-error response has no unknownField
    data.unknownField
    void message
  }
  if (error?.detail) {
    const location: (string | number)[] | undefined = error.detail[0]?.loc
    void location
  }
}
void contract
