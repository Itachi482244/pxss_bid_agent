import { useCallback, useEffect, useState } from "react";

import {
  getMatrixReview,
  type ComplianceItem,
  type DocumentChunk,
  type MatrixReviewDocument,
  type MatrixReviewDuplicateGroup,
  type MatrixReviewHighlight,
  type MatrixReviewUncoveredChunk
} from "../../../api/bid";

type ReviewChunk = Pick<
  DocumentChunk,
  "id" | "chunk_index" | "page_no" | "heading_path" | "content_text" | "document_version_id"
>;

type UseMatrixReviewOptions = {
  activeTab: string;
  selectedProjectId?: string;
  selectedSectionId?: string;
  setComplianceItems: (items: ComplianceItem[]) => void;
};

export function useMatrixReview({
  activeTab,
  selectedProjectId,
  selectedSectionId,
  setComplianceItems
}: UseMatrixReviewOptions) {
  const [reviewChunks, setReviewChunks] = useState<ReviewChunk[]>([]);
  const [loadingReviewChunks, setLoadingReviewChunks] = useState(false);
  const [reviewOpenXmlDocument, setReviewOpenXmlDocument] = useState<MatrixReviewDocument | null>(null);
  const [reviewHighlights, setReviewHighlights] = useState<MatrixReviewHighlight[]>([]);
  const [reviewUncoveredChunks, setReviewUncoveredChunks] = useState<MatrixReviewUncoveredChunk[]>([]);
  const [reviewDuplicateGroups, setReviewDuplicateGroups] = useState<MatrixReviewDuplicateGroup[]>([]);

  const applyReview = useCallback(
    (review: Awaited<ReturnType<typeof getMatrixReview>>) => {
      setReviewChunks(review.chunks);
      setReviewOpenXmlDocument(review.review_document);
      setReviewHighlights(review.highlights);
      setComplianceItems(review.items);
      setReviewUncoveredChunks(review.uncovered_chunks);
      setReviewDuplicateGroups(review.duplicate_groups);
    },
    [setComplianceItems]
  );

  const clearReview = useCallback(() => {
    setReviewChunks([]);
    setReviewOpenXmlDocument(null);
    setReviewHighlights([]);
    setReviewUncoveredChunks([]);
    setReviewDuplicateGroups([]);
  }, []);

  const reloadMatrixReview = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId || activeTab !== "review") return;
    const review = await getMatrixReview(selectedProjectId, selectedSectionId);
    applyReview(review);
    return review;
  }, [activeTab, applyReview, selectedProjectId, selectedSectionId]);

  useEffect(() => {
    if (activeTab !== "review" || !selectedProjectId || !selectedSectionId) return;
    let active = true;
    setLoadingReviewChunks(true);
    getMatrixReview(selectedProjectId, selectedSectionId)
      .then((review) => {
        if (active) applyReview(review);
      })
      .catch(() => {
        if (active) clearReview();
      })
      .finally(() => {
        if (active) setLoadingReviewChunks(false);
      });
    return () => {
      active = false;
    };
  }, [activeTab, applyReview, clearReview, selectedProjectId, selectedSectionId]);

  return {
    loadingReviewChunks,
    reloadMatrixReview,
    reviewChunks,
    reviewDuplicateGroups,
    reviewHighlights,
    reviewOpenXmlDocument,
    reviewUncoveredChunks,
    setLoadingReviewChunks,
    setReviewChunks,
    setReviewDuplicateGroups,
    setReviewHighlights,
    setReviewOpenXmlDocument,
    setReviewUncoveredChunks
  };
}
