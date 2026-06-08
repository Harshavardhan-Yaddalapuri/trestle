export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message?: string,
  ) {
    super(message || `API error ${status}`);
    this.name = "ApiError";
  }
}
