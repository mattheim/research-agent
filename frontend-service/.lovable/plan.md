

## Fix: send-email Edge Function Build Error

The build is failing because of a TypeScript strict error -- the `catch` block uses `error.message` but `error` is typed as `unknown` in strict mode.

### Change

In `supabase/functions/send-email/index.ts`, line 52, cast the error properly:

```typescript
// Before (line 51-53):
} catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {

// After:
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(JSON.stringify({ error: message }), {
```

That single change will resolve the `TS18046` build error and allow the function to deploy successfully.

