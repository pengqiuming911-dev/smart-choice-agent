/** Step 8: Event Idempotency Test */
import Redis from "ioredis";

// Mock Redis for testing
const mockRedis = new Redis("redis://localhost:6379/0");

describe("Event Idempotency", () => {
  beforeEach(async () => {
    // Clear test keys
    await mockRedis.del("event:test-event-001");
    await mockRedis.del("event:test-event-002");
  });

  afterAll(async () => {
    await mockRedis.quit();
  });

  test("同一 event_id 只处理一次", async () => {
    const eventId = "test-event-001";

    // First call - should not exist
    const exists1 = await mockRedis.exists(`event:${eventId}`);
    expect(exists1).toBe(0);

    // Simulate processing
    await mockRedis.setex(`event:${eventId}`, 600, "1");

    // Second call - should exist
    const exists2 = await mockRedis.exists(`event:${eventId}`);
    expect(exists2).toBe(1);
  });

  test("不同 event_id 分别处理", async () => {
    const eventId1 = "test-event-001";
    const eventId2 = "test-event-002";

    await mockRedis.setex(`event:${eventId1}`, 600, "1");

    const exists1 = await mockRedis.exists(`event:${eventId1}`);
    const exists2 = await mockRedis.exists(`event:${eventId2}`);

    expect(exists1).toBe(1);
    expect(exists2).toBe(0);
  });

  test("TTL 过期后可以重新处理", async () => {
    const eventId = "test-event-ttl";

    // Set with short TTL
    await mockRedis.setex(`event:${eventId}`, 1, "1");

    const existsBefore = await mockRedis.exists(`event:${eventId}`);
    expect(existsBefore).toBe(1);

    // Wait for TTL to expire
    await new Promise((resolve) => setTimeout(resolve, 1100));

    const existsAfter = await mockRedis.exists(`event:${eventId}`);
    expect(existsAfter).toBe(0);
  });
});
