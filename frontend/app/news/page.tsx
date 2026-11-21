import type { Metadata } from "next";
import { NewsFeed } from "@/components/news-feed";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = { title: "AI News Feed · MarketLens AI" };

export default function NewsPage() {
  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-lg font-semibold">AI News Feed</h1>
        <p className="text-xs text-muted">
          Each card is one article judged for one company: the same story can be bullish for one
          company and bearish for another. Explanations quote the source verbatim; headlines link to
          the original publisher.
        </p>
      </div>
      <Card>
        <CardContent>
          <NewsFeed />
        </CardContent>
      </Card>
    </div>
  );
}
