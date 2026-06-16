import { useCallback, useState } from "react";

import {
  getEnterpriseMaterialIndexHealth,
  getEnterpriseProfile,
  listEnterpriseMaterials,
  type EnterpriseMaterial,
  type EnterpriseMaterialIndexHealth,
  type EnterpriseProfile
} from "../../../api/bid";

export type EnterpriseProfileDraft = {
  companyName: string;
  unifiedSocialCreditCode: string;
  legalRepresentative: string;
  registeredAddress: string;
  businessScope: string;
  regionPreferences: string[];
  industryPreferences: string[];
  forbiddenRulesText: string;
};

type UseEnterpriseMaterialsOptions = {
  formatError: (error: unknown, fallback: string) => string;
  onError: (message: string) => void;
};

const emptyProfileDraft: EnterpriseProfileDraft = {
  companyName: "",
  unifiedSocialCreditCode: "",
  legalRepresentative: "",
  registeredAddress: "",
  businessScope: "",
  regionPreferences: [],
  industryPreferences: [],
  forbiddenRulesText: ""
};

function profileToDraft(profile: EnterpriseProfile): EnterpriseProfileDraft {
  return {
    companyName: profile.company_name,
    unifiedSocialCreditCode: profile.unified_social_credit_code ?? "",
    legalRepresentative: profile.legal_representative ?? "",
    registeredAddress: profile.registered_address ?? "",
    businessScope: profile.business_scope ?? "",
    regionPreferences: profile.region_preferences ?? [],
    industryPreferences: profile.industry_preferences ?? [],
    forbiddenRulesText: (profile.forbidden_rules ?? []).join("\n")
  };
}

export function useEnterpriseMaterials({ formatError, onError }: UseEnterpriseMaterialsOptions) {
  const [enterpriseProfile, setEnterpriseProfile] = useState<EnterpriseProfile | null>(null);
  const [enterpriseMaterials, setEnterpriseMaterials] = useState<EnterpriseMaterial[]>([]);
  const [materialIndexHealth, setMaterialIndexHealth] = useState<EnterpriseMaterialIndexHealth | null>(null);
  const [loadingEnterprise, setLoadingEnterprise] = useState(false);
  const [loadingMaterialIndexHealth, setLoadingMaterialIndexHealth] = useState(false);
  const [rebuildingMaterialIndex, setRebuildingMaterialIndex] = useState(false);
  const [savingEnterprise, setSavingEnterprise] = useState(false);
  const [profileDraft, setProfileDraft] = useState<EnterpriseProfileDraft>(emptyProfileDraft);

  const reloadMaterialIndexHealth = useCallback(async () => {
    setLoadingMaterialIndexHealth(true);
    try {
      const health = await getEnterpriseMaterialIndexHealth();
      setMaterialIndexHealth(health);
      return health;
    } catch (error) {
      onError(formatError(error, "企业资料索引状态加载失败"));
      return null;
    } finally {
      setLoadingMaterialIndexHealth(false);
    }
  }, [formatError, onError]);

  const reloadEnterprise = useCallback(async () => {
    setLoadingEnterprise(true);
    try {
      const [profile, materials, indexHealth] = await Promise.all([
        getEnterpriseProfile(),
        listEnterpriseMaterials({ limit: 100 }),
        getEnterpriseMaterialIndexHealth()
      ]);
      setEnterpriseProfile(profile);
      setEnterpriseMaterials(materials);
      setMaterialIndexHealth(indexHealth);
      if (profile) setProfileDraft(profileToDraft(profile));
    } catch (error) {
      onError(formatError(error, "企业资料加载失败"));
    } finally {
      setLoadingEnterprise(false);
    }
  }, [formatError, onError]);

  return {
    enterpriseMaterials,
    enterpriseProfile,
    loadingEnterprise,
    loadingMaterialIndexHealth,
    materialIndexHealth,
    profileDraft,
    rebuildingMaterialIndex,
    reloadEnterprise,
    reloadMaterialIndexHealth,
    savingEnterprise,
    setEnterpriseMaterials,
    setEnterpriseProfile,
    setLoadingEnterprise,
    setLoadingMaterialIndexHealth,
    setMaterialIndexHealth,
    setProfileDraft,
    setRebuildingMaterialIndex,
    setSavingEnterprise
  };
}
