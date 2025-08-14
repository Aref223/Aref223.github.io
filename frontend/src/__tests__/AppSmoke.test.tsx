import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

it('renders App shell', () => {
  // Avoid redirect loop by pre-setting a token
  localStorage.setItem('token', 'test')
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>
  )
})