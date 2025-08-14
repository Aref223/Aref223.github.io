import { render, screen } from '@testing-library/react'
import Login from '../pages/Login'
import { MemoryRouter } from 'react-router-dom'

it('renders login fields', () => {
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  )
  expect(screen.getAllByText(/Login/i)[0]).toBeInTheDocument()
  expect(screen.getByPlaceholderText(/Email/)).toBeInTheDocument()
  expect(screen.getByPlaceholderText(/Password/)).toBeInTheDocument()
})