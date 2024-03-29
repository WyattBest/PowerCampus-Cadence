USE [Campus6]
GO

/****** Object:  StoredProcedure [custom].[CadenceSelContact]    Script Date: 2020-12-22 23:48:35 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


-- =============================================
-- Author:		Wyatt Best
-- Create date: 2020-11-30
-- Description:	Selects core demographic fields for a single contact.
--
-- =============================================
CREATE PROCEDURE [custom].[CadenceSelContact] @PCID NVARCHAR(10)
	,@Dept NVARCHAR(2)
AS
BEGIN
	SET NOCOUNT ON;

	SELECT PEOPLE_CODE_ID [uniqueCampusId]
		,dbo.fnPeopleOrgName(PEOPLE_CODE_ID, 'FN') [firstName]
		,dbo.fnPeopleOrgName(PEOPLE_CODE_ID, 'LN') [lastName]
		,Phone.*
		,CASE T.[STATUS]
			WHEN 'A'
				THEN 0
			WHEN 'I'
				THEN 1
			ELSE NULL
			END AS [optedOut]
	FROM PEOPLE P
	OUTER APPLY (
		SELECT TOP 1 CASE 
				WHEN LEFT(PP.PhoneNumber, 1) = '1' --US country code already prepended
					THEN PP.PhoneNumber
				ELSE '1' + PP.PhoneNumber
				END AS [mobileNumber]
		FROM PersonPhone PP
		WHERE PP.PersonId = P.PersonId
			AND DoNotCallReason IS NULL
			AND PhoneType = 'MOBILE1'
			AND CountryId = 240 --US numbers only
		ORDER BY CASE 
				WHEN P.PrimaryPhoneId = PP.PersonPhoneId
					THEN GETDATE()
				ELSE PP.Revision_Date + PP.Revision_Time
				END DESC
		) AS Phone
	LEFT JOIN TELECOMMUNICATIONS T
		ON T.PEOPLE_ORG_CODE_ID = P.PEOPLE_CODE_ID
			AND T.COM_TYPE = 'SMS' + @Dept
	WHERE PEOPLE_CODE_ID = @PCID
		--ORDER BY PEOPLE_CODE_ID --Debug
END
GO

